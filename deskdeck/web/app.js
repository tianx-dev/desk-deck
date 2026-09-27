(function () {
  "use strict";
  const $ = (id) => document.getElementById(id),
    session = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  let model = { tasks: [], notifications: [], mode: "demo" },
    online = false,
    view = "desk",
    selected = null,
    toastTimer,
    lastNotice = "",
    quiet = localStorage.getItem("deckQuiet") === "1",
    minutes = 25,
    focusEnd = 0,
    pausedSeconds = 0,
    focusRunning = false,
    previousFocus = false;
  try {
    const saved = JSON.parse(localStorage.getItem("deckFocus") || "null");
    if (saved) {
      focusEnd = saved.end;
      minutes = saved.minutes;
      focusRunning = focusEnd > Date.now() && !saved.paused;
      pausedSeconds = saved.paused || 0;
    }
  } catch (e) {}
  let pairingKey = sessionStorage.getItem("deskPairingKey") || "";
  const fragment = new URLSearchParams(location.hash.slice(1));
  if (fragment.has("key")) {
    pairingKey = fragment.get("key");
    sessionStorage.setItem("deskPairingKey", pairingKey);
    history.replaceState(null, "", location.pathname + location.search);
  }
  function authHeaders(extra) {
    return Object.assign(
      {},
      extra || {},
      pairingKey ? { Authorization: "Bearer " + pairingKey } : {},
    );
  }
  function icon(id) {
    const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"),
      u = document.createElementNS(s.namespaceURI, "use");
    u.setAttribute("href", "#i-" + id);
    s.appendChild(u);
    return s;
  }
  function el(tag, cls, text) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function age(t) {
    const s = Math.max(0, Math.floor(Date.now() / 1000 - t));
    return s < 10
      ? "just now"
      : s < 60
        ? s + "s ago"
        : s < 3600
          ? Math.floor(s / 60) + "m ago"
          : s < 86400
            ? Math.floor(s / 3600) + "h ago"
            : Math.floor(s / 86400) + "d ago";
  }
  const labels = {
    active: "Working",
    ready: "Ready to review",
    quiet: "Quiet",
    unknown: "Last activity",
    stopped: "Interrupted",
  };
  function stateLine(task) {
    return (labels[task.state] || "Last activity") + " · " + age(task.updated);
  }
  function toast(text) {
    $("toast").textContent = text;
    $("toast").classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $("toast").classList.remove("show"), 3200);
  }
  async function action(name, target, extra) {
    const r = await fetch("/api/action", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        action: name,
        target: target,
        session: session,
        extra: extra || {},
      }),
    });
    const d = await r.json();
    if (!r.ok) throw Error(d.error || "Could not connect to your Mac");
    return d;
  }
  function network(good) {
    online = good;
    $("connection").classList.toggle("off", !good);
    $("connection").querySelector("span").textContent = good
      ? model.mode === "demo"
        ? "Synthetic demo feed"
        : "Connected to your local server"
      : "Feed offline or unpaired";
    $("offline").classList.toggle("show", !good);
    document.querySelectorAll(".launch").forEach((n) => (n.disabled = !good));
    $("opentask").disabled = !good || (selected && !selected.open_url);
  }
  function switchView(name) {
    view = name;
    document
      .querySelectorAll(".view")
      .forEach((n) => n.classList.toggle("on", n.id === "view-" + name));
    document.querySelectorAll(".tab").forEach((n) => {
      n.classList.toggle("selected", n.dataset.view === name);
      n.setAttribute(
        "aria-current",
        n.dataset.view === name ? "page" : "false",
      );
    });
    if (name === "tasks") renderTasks();
    if (name === "activity") renderNotices();
    $("tip").textContent =
      name === "desk"
        ? "One tap. Back to your work."
        : name === "tasks"
          ? "Latest recorded updates. No guessed percentages."
          : "New results appear here, quietly.";
  }
  function showTask(id) {
    selected = model.tasks.find((t) => t.id === id);
    if (!selected) {
      toast("This task left the recent-task feed");
      return;
    }
    $("detailtitle").textContent = selected.title;
    $("detailstate").textContent = stateLine(selected);
    $("detailstate").className = "state " + selected.state;
    $("detailtext").textContent =
      selected.summary ||
      "No recent message is available. Open the task on your Mac for context.";
    $("opentask").disabled = !online || !selected.open_url;
    $("detail").classList.add("show");
    $("closedetail").focus();
  }
  function closeDetail() {
    $("detail").classList.remove("show");
    selected = null;
  }
  function taskButton(task, full) {
    const b = el("button", full ? "taskkey" : "update");
    b.appendChild(el("span", "state " + task.state, stateLine(task)));
    b.appendChild(el("h3", "", task.title));
    b.appendChild(el("p", "", task.summary || "Open the task for context."));
    b.onclick = () => showTask(task.id);
    return b;
  }
  function configureLaunchers() {
    document.querySelectorAll(".launch").forEach((b, i) => {
      const item = (model.launchers || [])[i];
      b.hidden = !item;
      b.style.display = item ? "" : "none";
      if (item) {
        b.dataset.app = item.id;
        b.querySelector(".keyname").textContent = item.label;
        b.querySelector(".sub").textContent = item.subtitle;
        b.querySelector(".icon use").setAttribute("href", "#i-" + item.icon);
      }
    });
  }
  function renderTasks() {
    const target = $("taskgrid");
    const signature = model.tasks.map((t) => t.id).join();
    if (!model.tasks.length) {
      target.replaceChildren(
        el(
          "p",
          "small",
          "Your connected jobs will appear here. Publish a task update from your computer.",
        ),
      );
      target.dataset.ids = "";
      return;
    }
    if (target.dataset.ids !== signature) {
      target.replaceChildren(...model.tasks.map((t) => taskButton(t, true)));
      target.dataset.ids = signature;
    } else {
      Array.from(target.children).forEach((n, i) => {
        const t = model.tasks[i];
        n.querySelector(".state").textContent = stateLine(t);
        n.querySelector(".state").className = "state " + t.state;
        n.querySelector("p").textContent =
          t.summary || "Open the task for context.";
      });
    }
  }
  function renderRail() {
    const target = $("railTasks");
    const rank = (t) =>
      t.state === "active"
        ? 3
        : t.state === "ready" && Date.now() / 1000 - t.updated < 86400
          ? 2
          : 0;
    const tasks = model.tasks
      .slice()
      .sort((a, b) => rank(b) - rank(a) || b.updated - a.updated)
      .slice(0, 2);
    const signature = tasks.map((t) => t.id).join();
    if (target.dataset.ids !== signature) {
      target.replaceChildren(...tasks.map((t) => taskButton(t, false)));
      target.dataset.ids = signature;
    } else {
      Array.from(target.children).forEach((n, i) => {
        const t = tasks[i];
        n.querySelector(".state").textContent = stateLine(t);
        n.querySelector(".state").className = "state " + t.state;
        n.querySelector("p").textContent =
          t.summary || "Open the task for context.";
      });
    }
  }
  function renderNotices() {
    const target = $("activitylist");
    target.replaceChildren();
    if (!model.notifications.length) {
      const empty = el("div", "empty");
      empty.append(
        icon("check"),
        el("h3", "", "Nothing new needs a glance."),
        el(
          "p",
          "",
          "New task results will collect here. Your existing history stays in Tasks.",
        ),
      );
      target.append(empty);
      return;
    }
    model.notifications.forEach((n) => {
      const row = el("div", "notice" + (n.read ? " read" : "")),
        body = el("main");
      body.append(
        el("span", "state ready", "Ready to review · " + age(n.at)),
        el("h3", "", n.title),
        el("p", "", n.message),
      );
      const open = el("button", "btn", "Open");
      open.onclick = async () => {
        try {
          const result = await action("open_task", n.task);
          await action("acknowledge", n.id);
          toast(
            result.simulated
              ? "Preview: would open this task"
              : "Opened on your Mac",
          );
          poll();
        } catch (e) {
          toast(e.message);
        }
      };
      row.append(body, open);
      target.append(row);
    });
  }
  async function poll() {
    try {
      const r = await fetch("/api/state", {
        cache: "no-store",
        headers: authHeaders(),
      });
      if (!r.ok) throw Error();
      const next = await r.json();
      if (!next.ok) throw Error();
      model = next;
      network(true);
      configureLaunchers();
      $("demo-banner").classList.toggle("show", model.mode === "demo");
      $("coverage").textContent =
        model.mode === "demo"
          ? "Fictional tasks. No private data or real app launches."
          : model.coverage || "Your connected tasks";
      const count = model.notifications.filter((n) => !n.read).length;
      $("activecount").textContent = model.tasks.filter(
        (t) => t.state === "active",
      ).length;
      $("newcount").textContent = count;
      $("badge").textContent = count;
      $("freshness").textContent = "Updated " + age(model.checked);
      if (document.querySelector('[data-app="codex"]'))
        document.querySelector('[data-app="codex"] .sub').textContent =
          model.tasks.filter((t) => t.state === "active").length +
          (model.mode === "demo"
            ? " active in this demo"
            : " active on this Mac");
      renderRail();
      if (view === "tasks") renderTasks();
      if (view === "activity") renderNotices();
      const recent = model.notifications.find((n) => !n.read);
      if (recent && recent.id !== lastNotice) {
        lastNotice = recent.id;
        if (
          !quiet &&
          !focusRunning &&
          !$("focusview").classList.contains("show")
        )
          toast("Ready to review: " + recent.title);
      }
    } catch (e) {
      network(false);
      $("freshness").textContent = model.checked
        ? "Last update " + age(model.checked)
        : "Unavailable";
    }
  }
  function quietState() {
    $("quiet").classList.toggle("on", quiet);
    $("quiet").setAttribute("aria-pressed", String(quiet));
    $("quiet").querySelector("span").textContent = quiet ? "Quiet on" : "Quiet";
    localStorage.setItem("deckQuiet", quiet ? "1" : "0");
  }
  $("quiet").onclick = () => {
    quiet = !quiet;
    quietState();
    toast(
      quiet
        ? "Quiet mode: updates stay in Activity"
        : "New result banners are on",
    );
  };
  quietState();
  document
    .querySelectorAll(".tab")
    .forEach((n) => (n.onclick = () => switchView(n.dataset.view)));
  document.querySelectorAll(".launch").forEach(
    (b) =>
      (b.onclick = async () => {
        if (b.dataset.busy === "1") return;
        b.dataset.busy = "1";
        try {
          const result = await action("open_app", b.dataset.app);
          b.classList.add("launched");
          toast(
            (result.simulated ? "Preview: would open " : "Opened ") +
              b.querySelector(".keyname").textContent,
          );
          setTimeout(() => b.classList.remove("launched"), 1000);
        } catch (e) {
          toast(e.message);
        } finally {
          setTimeout(() => (b.dataset.busy = "0"), 700);
        }
      }),
  );
  $("opentask").onclick = async () => {
    if (!selected) return;
    $("opentask").disabled = true;
    try {
      const result = await action("open_task", selected.id);
      toast(
        result.simulated
          ? "Preview: would open this task"
          : "Task opened on your Mac",
      );
      closeDetail();
    } catch (e) {
      toast(e.message);
    } finally {
      $("opentask").disabled = !online || (selected && !selected.open_url);
    }
  };
  $("closedetail").onclick = $("done").onclick = closeDetail;
  $("detail").onclick = (e) => {
    if (e.target === $("detail")) closeDetail();
  };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeDetail();
      $("focusview").classList.remove("show");
    }
  });
  $("clear").onclick = async () => {
    try {
      await action("acknowledge", "all");
      poll();
      toast("Activity marked seen");
    } catch (e) {
      toast(e.message);
    }
  };
  function saveFocus() {
    localStorage.setItem(
      "deckFocus",
      JSON.stringify({
        end: focusEnd,
        minutes: minutes,
        paused: pausedSeconds,
      }),
    );
  }
  function focusClock() {
    const sec = focusRunning
      ? Math.max(0, Math.ceil((focusEnd - Date.now()) / 1000))
      : pausedSeconds || minutes * 60;
    $("countdown").textContent =
      String(Math.floor(sec / 60)).padStart(2, "0") +
      ":" +
      String(sec % 60).padStart(2, "0");
    $("startfocus").textContent = focusRunning
      ? "Pause"
      : pausedSeconds
        ? "Resume"
        : "Start focus";
    $("focussub").textContent = focusRunning
      ? Math.ceil(sec / 60) + "m left · tap to return"
      : pausedSeconds
        ? "Paused · tap to resume"
        : "A little uninterrupted time";
    if (focusRunning && sec === 0) {
      focusRunning = false;
      focusEnd = 0;
      saveFocus();
      toast("Focus complete. Take a breath.");
    }
    document
      .querySelectorAll("[data-min]")
      .forEach((b) =>
        b.classList.toggle("chosen", Number(b.dataset.min) === minutes),
      );
  }
  $("focuskey").onclick = () => {
    $("focusview").classList.add("show");
    focusClock();
  };
  $("backdesk").onclick = () => {
    $("focusview").classList.remove("show");
  };
  $("startfocus").onclick = () => {
    if (focusRunning) {
      pausedSeconds = Math.max(1, Math.ceil((focusEnd - Date.now()) / 1000));
      focusRunning = false;
    } else {
      focusEnd = Date.now() + (pausedSeconds || minutes * 60) * 1000;
      pausedSeconds = 0;
      focusRunning = true;
      action("focus", null, { minutes: minutes }).catch(() => {});
    }
    saveFocus();
    focusClock();
  };
  document.querySelectorAll("[data-min]").forEach(
    (b) =>
      (b.onclick = () => {
        minutes = Number(b.dataset.min);
        focusRunning = false;
        focusEnd = 0;
        pausedSeconds = 0;
        saveFocus();
        focusClock();
      }),
  );
  function clock() {
    const d = new Date();
    $("clock").textContent = d
      .toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
      .replace(/\s*[AP]M/, "");
    $("date").textContent = d.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    focusClock();
  }
  clock();
  setInterval(clock, 1000);
  let swipe = null,
    suppressClickUntil = 0;
  document.addEventListener(
    "click",
    (e) => {
      if (Date.now() < suppressClickUntil) {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
    },
    true,
  );
  $("swipearea").addEventListener("pointerdown", (e) => {
    if (e.pointerType === "touch") swipe = { x: e.clientX, y: e.clientY };
  });
  $("swipearea").addEventListener("pointerup", (e) => {
    if (!swipe) return;
    const dx = e.clientX - swipe.x,
      dy = e.clientY - swipe.y;
    swipe = null;
    if (Math.abs(dx) > 100 && Math.abs(dy) < 45) {
      suppressClickUntil = Date.now() + 400;
      const views = ["desk", "tasks", "activity"];
      switchView(views[(views.indexOf(view) + (dx < 0 ? 1 : 2)) % 3]);
    }
  });
  document.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "touch")
      action("touch", null, {
        x: Math.round(e.clientX),
        y: Math.round(e.clientY),
        pointerType: e.pointerType,
        version: "public-1",
      }).catch(() => {});
  });
  function heartbeat() {
    action("heartbeat", null, {
      width: innerWidth,
      height: innerHeight,
      touch: navigator.maxTouchPoints || 0,
      version: "public-1",
      view: view,
    }).catch(() => {});
  }
  network(false);
  poll();
  heartbeat();
  setInterval(poll, 4000);
  setInterval(heartbeat, 15000);
})();
