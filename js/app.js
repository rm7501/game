// UI for حزّورة: board, keyboard, sheets and persistence. Rules live in logic.js.
(function () {
  "use strict";

  var L = window.HZLogic;
  var TITLE = "حزّورة";
  var STORE_PREFIX = "hazzoora:";
  var FLIP_STAGGER = 280;
  var KEY_ROWS = [
    ["ض", "ص", "ث", "ق", "ف", "غ", "ع", "ه", "خ", "ح", "ج", "د"],
    ["ش", "س", "ي", "ب", "ل", "ا", "ت", "ن", "م", "ك", "ط", "ذ"],
    ["enter", "ئ", "ء", "ؤ", "ر", "ى", "ة", "و", "ز", "ظ", "back"]
  ];
  // Physical key positions of the standard Arabic (101) layout, so players on an
  // English layout can still type by position.
  var CODE_MAP = {
    KeyQ: "ض", KeyW: "ص", KeyE: "ث", KeyR: "ق", KeyT: "ف", KeyY: "غ", KeyU: "ع",
    KeyI: "ه", KeyO: "خ", KeyP: "ح", BracketLeft: "ج", BracketRight: "د",
    KeyA: "ش", KeyS: "س", KeyD: "ي", KeyF: "ب", KeyG: "ل", KeyH: "ا", KeyJ: "ت",
    KeyK: "ن", KeyL: "م", Semicolon: "ك", Quote: "ط",
    KeyZ: "ئ", KeyX: "ء", KeyC: "ؤ", KeyV: "ر", KeyB: "لا", KeyN: "ى", KeyM: "ة",
    Comma: "و", Period: "ز", Slash: "ظ", Backquote: "ذ"
  };
  var WIN_WORDS = ["عبقري!", "مذهل!", "رائع!", "ممتاز!", "أحسنت!", "نجوت بأعجوبة!"];
  var ORDINALS = ["الأول", "الثاني", "الثالث", "الرابع", "الخامس"];
  var STATE_LABEL = { correct: "في مكانه الصحيح", present: "في مكان آخر", absent: "غير موجود" };

  var answers = window.HZ_ANSWERS.map(function (w) { return { word: w, key: L.normalizeWord(w) }; });
  var valid = new Set(window.HZ_VALID_WORDS);
  answers.forEach(function (a) { valid.add(a.key); });

  var $ = function (sel) { return document.querySelector(sel); };
  var digits = L.toArabicDigits;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  // ---------- storage (best effort: private windows may refuse it) ----------
  var storage = {
    get: function (key, fallback) {
      try {
        var raw = window.localStorage.getItem(STORE_PREFIX + key);
        return raw ? JSON.parse(raw) : fallback;
      } catch (e) { return fallback; }
    },
    set: function (key, value) {
      try { window.localStorage.setItem(STORE_PREFIX + key, JSON.stringify(value)); } catch (e) {}
    }
  };

  // ---------- state ----------
  var settings = Object.assign(
    { hardMode: false, theme: null, highContrast: false, onscreenOnly: false },
    storage.get("settings", {})
  );
  var stats = Object.assign(L.emptyStats(), storage.get("stats", {}));
  var today, puzzle, game, results;
  var current = [];
  var busy = false;

  var boardEl = $("#board");
  var keyboardEl = $("#keyboard");
  var rowEls = [];
  var keyEls = {};

  function loadDay() {
    today = L.dayIndex(new Date());
    puzzle = L.answerForDay(today, answers);
    var saved = storage.get("game", null);
    if (saved && saved.day === today && Array.isArray(saved.guesses)) {
      game = saved;
    } else {
      game = { day: today, guesses: [], status: "playing", hard: settings.hardMode };
    }
    results = game.guesses.map(function (g) { return L.evaluateGuess(g, puzzle.key); });
    current = [];
    L.refreshStreak(stats, today);
  }

  function saveGame() { storage.set("game", game); }
  function saveStats() { storage.set("stats", stats); }
  function saveSettings() { storage.set("settings", settings); }

  function history() {
    return game.guesses.map(function (g, i) { return { guess: g, result: results[i] }; });
  }

  // ---------- board ----------
  function buildBoard() {
    boardEl.textContent = "";
    rowEls = [];
    for (var r = 0; r < L.MAX_GUESSES; r++) {
      var row = document.createElement("div");
      row.className = "row";
      row.setAttribute("role", "group");
      row.setAttribute("aria-label", "التخمين " + digits(r + 1));
      for (var c = 0; c < L.WORD_LENGTH; c++) {
        var tile = document.createElement("div");
        tile.className = "tile";
        tile.setAttribute("role", "img");
        row.appendChild(tile);
      }
      boardEl.appendChild(row);
      rowEls.push(row);
    }
  }

  function setTile(tile, index, letter, state) {
    tile.textContent = letter || "";
    if (letter) tile.setAttribute("data-filled", "");
    else tile.removeAttribute("data-filled");
    if (state) tile.setAttribute("data-state", state);
    else tile.removeAttribute("data-state");
    tile.setAttribute(
      "aria-label",
      "الحرف " + ORDINALS[index] + ": " + (letter ? letter + (state ? "، " + STATE_LABEL[state] : "") : "فارغ")
    );
  }

  function paintBoard() {
    rowEls.forEach(function (row, r) {
      var guess = game.guesses[r];
      var letters = guess ? Array.from(guess) : (r === game.guesses.length ? current : []);
      Array.prototype.forEach.call(row.children, function (tile, c) {
        setTile(tile, c, letters[c], guess ? results[r][c] : null);
      });
    });
  }

  function fitBoard() {
    var wrap = $("#board-wrap");
    var h = Math.min(wrap.clientHeight - 8, 420);
    var w = Math.min(Math.floor(h * 5 / 6), wrap.clientWidth, 350);
    if (w <= 0) return;
    boardEl.style.width = w + "px";
    boardEl.style.height = Math.floor(w * 6 / 5) + "px";
    boardEl.style.setProperty("--tile-font", Math.max(14, Math.round(w / 5 * 0.5)) + "px");
  }

  // ---------- keyboard ----------
  function buildKeyboard() {
    keyboardEl.textContent = "";
    keyEls = {};
    KEY_ROWS.forEach(function (keys) {
      var row = document.createElement("div");
      row.className = "kb-row";
      keys.forEach(function (k) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "key";
        btn.dataset.key = k;
        if (k === "enter") {
          btn.classList.add("wide");
          btn.textContent = "إدخال";
        } else if (k === "back") {
          btn.classList.add("wide");
          btn.setAttribute("aria-label", "حذف");
          btn.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" class="stroke"><path d="M3 5h12l6 7-6 7H3z"/><path d="M7.5 9.5l5 5M12.5 9.5l-5 5"/></svg>';
        } else {
          btn.textContent = k;
          keyEls[k] = btn;
        }
        row.appendChild(btn);
      });
      keyboardEl.appendChild(row);
    });
  }

  function paintKeyboard() {
    var states = L.keyboardStates(history());
    Object.keys(keyEls).forEach(function (k) {
      var btn = keyEls[k];
      if (states[k]) {
        btn.dataset.state = states[k];
        btn.setAttribute("aria-label", k + "، " + STATE_LABEL[states[k]]);
      } else {
        delete btn.dataset.state;
        btn.removeAttribute("aria-label");
      }
    });
  }

  // ---------- input ----------
  function addLetter(ch) {
    if (busy || game.status !== "playing" || current.length >= L.WORD_LENGTH) return;
    current.push(ch);
    var r = game.guesses.length;
    var tile = rowEls[r].children[current.length - 1];
    setTile(tile, current.length - 1, ch, null);
    replay(tile, "pop");
  }

  function removeLetter() {
    if (busy || game.status !== "playing" || !current.length) return;
    current.pop();
    var tile = rowEls[game.guesses.length].children[current.length];
    setTile(tile, current.length, "", null);
  }

  function rejectGuess(message) {
    toast(message);
    replay(rowEls[game.guesses.length], "shake");
  }

  function submitGuess() {
    if (busy || game.status !== "playing") return;
    if (current.length < L.WORD_LENGTH) return rejectGuess("عدد الأحرف غير كافٍ");
    var guess = current.join("");
    if (!valid.has(guess)) return rejectGuess("الكلمة ليست في القائمة");
    if (settings.hardMode) {
      var v = L.hardModeViolation(guess, history());
      if (v && v.type === "position") return rejectGuess("الحرف " + ORDINALS[v.index] + " يجب أن يكون «" + v.letter + "»");
      if (v) return rejectGuess("يجب أن يحتوي التخمين على «" + v.letter + "»");
    }

    var result = L.evaluateGuess(guess, puzzle.key);
    var rowIndex = game.guesses.length;
    game.hard = rowIndex === 0 ? settings.hardMode : Boolean(game.hard && settings.hardMode);
    game.guesses.push(guess);
    results.push(result);
    current = [];
    var won = result.every(function (s) { return s === "correct"; });
    if (won) game.status = "won";
    else if (game.guesses.length === L.MAX_GUESSES) game.status = "lost";
    // Save before the animation so a reload mid-flip cannot undo the guess.
    saveGame();
    if (game.status !== "playing") {
      L.recordResult(stats, today, won, game.guesses.length);
      saveStats();
    }

    busy = true;
    revealRow(rowIndex, guess, result).then(function () {
      paintKeyboard();
      announce(Array.from(guess).map(function (ch, i) { return ch + " " + STATE_LABEL[result[i]]; }).join("، "));
      if (won) {
        toast(WIN_WORDS[rowIndex], 2000);
        return hopRow(rowIndex).then(function () { busy = false; later(openStats, 1200); });
      }
      busy = false;
      if (game.status === "lost") {
        toast(puzzle.word, 5000, "answer");
        later(openStats, 2200);
      }
    });
  }

  function revealRow(r, guess, result) {
    var letters = Array.from(guess);
    var tiles = Array.prototype.slice.call(rowEls[r].children);
    var stagger = reduceMotion.matches ? 0 : FLIP_STAGGER;
    return Promise.all(tiles.map(function (tile, i) {
      return wait(i * stagger)
        .then(function () { return play(tile, "flip-in", 300); })
        .then(function () {
          setTile(tile, i, letters[i], result[i]);
          return play(tile, "flip-out", 300);
        });
    }));
  }

  function hopRow(r) {
    var tiles = Array.prototype.slice.call(rowEls[r].children);
    var step = reduceMotion.matches ? 0 : 90;
    return Promise.all(tiles.map(function (tile, i) {
      return wait(i * step).then(function () { return play(tile, "hop", 1000); });
    }));
  }

  // Run a CSS animation class once; resolves on animationend, or after a
  // timeout in case the browser skips the animation (background tab).
  function play(el, cls, maxMs) {
    return new Promise(function (resolve) {
      var done = false;
      function finish() {
        if (done) return;
        done = true;
        el.classList.remove(cls);
        el.removeEventListener("animationend", finish);
        resolve();
      }
      el.classList.remove(cls);
      void el.offsetWidth;
      el.classList.add(cls);
      el.addEventListener("animationend", finish);
      setTimeout(finish, reduceMotion.matches ? 50 : maxMs);
    });
  }

  function replay(el, cls) {
    el.classList.remove(cls);
    void el.offsetWidth;
    el.classList.add(cls);
    el.addEventListener("animationend", function () { el.classList.remove(cls); }, { once: true });
  }

  function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function later(fn, ms) { setTimeout(fn, ms); }

  function onKeyboardClick(e) {
    var btn = e.target.closest(".key");
    if (!btn) return;
    if (e.detail > 0) btn.blur(); // mouse/touch: keep focus off so Enter submits
    var k = btn.dataset.key;
    if (k === "enter") submitGuess();
    else if (k === "back") removeLetter();
    else addLetter(k);
  }

  function onKeyDown(e) {
    if (openSheet) {
      if (e.key === "Escape") closeSheet();
      else if (e.key === "Tab") trapFocus(e);
      return;
    }
    if (e.ctrlKey || e.metaKey || e.altKey || settings.onscreenOnly) return;
    var onButton = e.target.closest && e.target.closest("button, a, input, textarea");
    if (e.key === "Enter") {
      if (onButton) return; // let the focused control handle it
      e.preventDefault();
      submitGuess();
      return;
    }
    if (e.key === "Backspace") {
      e.preventDefault();
      removeLetter();
      return;
    }
    var letters = L.lettersFromInput(e.key);
    if (!letters.length && /^[\x21-\x7e]$/.test(e.key) && CODE_MAP[e.code]) {
      letters = L.lettersFromInput(CODE_MAP[e.code]);
    }
    if (letters.length) {
      e.preventDefault();
      letters.forEach(addLetter);
    }
  }

  // ---------- toasts & announcements ----------
  function toast(message, ms, variant) {
    var el = document.createElement("div");
    el.className = "toast" + (variant ? " " + variant : "");
    el.textContent = message;
    var box = $("#toasts");
    box.prepend(el);
    setTimeout(function () {
      el.classList.add("fade");
      setTimeout(function () { el.remove(); }, 320);
    }, ms || 1100);
  }

  function announce(text) {
    var el = $("#announcer");
    el.textContent = "";
    setTimeout(function () { el.textContent = text; }, 50);
  }

  // ---------- sheets ----------
  var openSheet = null;
  var opener = null;
  var openerByKeyboard = false;

  function openModal(id, trigger) {
    if (openSheet) closeSheet(true);
    openSheet = document.getElementById(id);
    opener = trigger || null;
    openerByKeyboard = Boolean(trigger && trigger.matches(":focus-visible"));
    openSheet.hidden = false;
    // Keyboard users land on the close button; pointer users get no focus ring.
    var focusTarget = openerByKeyboard ? openSheet.querySelector("[data-close]") : openSheet.querySelector(".sheet");
    focusTarget.focus({ preventScroll: true });
  }

  function closeSheet(silent) {
    if (!openSheet) return;
    openSheet.hidden = true;
    if (openSheet.id === "modal-stats") stopCountdown();
    if (openSheet.id === "modal-help") storage.set("seenHelp", true);
    openSheet = null;
    if (!silent && opener && openerByKeyboard) opener.focus();
    else if (document.activeElement) document.activeElement.blur();
    opener = null;
  }

  function trapFocus(e) {
    var items = openSheet.querySelectorAll("button:not([hidden]), a[href], textarea:not([hidden])");
    var visible = Array.prototype.filter.call(items, function (el) { return el.offsetParent !== null; });
    if (!visible.length) return;
    var first = visible[0];
    var last = visible[visible.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  // ---------- stats ----------
  var countdownTimer = null;

  function openStats(trigger) {
    renderStats();
    openModal("modal-stats", trigger);
    if (game.status !== "playing") startCountdown();
  }

  function renderStats() {
    var winPct = stats.played ? Math.round(stats.wins / stats.played * 100) : 0;
    $("#stat-played").textContent = digits(stats.played);
    $("#stat-winpct").textContent = digits(winPct);
    $("#stat-streak").textContent = digits(stats.currentStreak);
    $("#stat-max").textContent = digits(stats.maxStreak);

    var dist = $("#distribution");
    dist.textContent = "";
    var max = Math.max.apply(null, stats.distribution.concat([1]));
    stats.distribution.forEach(function (count, i) {
      var row = document.createElement("div");
      row.className = "dist-row";
      var label = document.createElement("span");
      label.className = "dist-label";
      label.textContent = digits(i + 1);
      var bar = document.createElement("span");
      bar.className = "dist-bar";
      if (game.status === "won" && game.guesses.length === i + 1) bar.classList.add("current");
      bar.style.width = Math.max(7, Math.round(count / max * 100)) + "%";
      bar.textContent = digits(count);
      row.setAttribute("aria-label", "بالتخمين " + digits(i + 1) + ": " + digits(count));
      row.appendChild(label);
      row.appendChild(bar);
      dist.appendChild(row);
    });

    var finished = game.status !== "playing";
    $("#round-end").hidden = !finished;
    $("#share-fallback").hidden = true;
    if (finished) $("#answer-word").textContent = puzzle.word;
    $("#puzzle-meta").textContent = TITLE + " رقم " + digits(today + 1) + " · " + hijriToday();
  }

  function hijriToday() {
    try {
      return new Intl.DateTimeFormat("ar-SA-u-ca-islamic-umalqura-nu-arab", {
        weekday: "long", day: "numeric", month: "long", year: "numeric"
      }).format(new Date());
    } catch (e) {
      return new Date().toLocaleDateString("ar");
    }
  }

  function startCountdown() {
    stopCountdown();
    var tick = function () {
      var ms = L.msUntilNextDay(new Date());
      var s = Math.floor(ms / 1000);
      var parts = [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60].map(function (n) {
        return digits(String(n).padStart(2, "0"));
      });
      $("#countdown").textContent = parts.join(":");
      if (L.dayIndex(new Date()) !== today) checkNewDay();
    };
    tick();
    countdownTimer = setInterval(tick, 1000);
  }

  function stopCountdown() {
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = null;
  }

  function isDark() {
    if (settings.theme) return settings.theme === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function shareResult() {
    var text = L.shareText({
      title: TITLE,
      number: today + 1,
      won: game.status === "won",
      hardMode: game.hard,
      highContrast: settings.highContrast,
      dark: isDark(),
      results: results
    });
    var touch = window.matchMedia("(pointer: coarse)").matches;
    var viaShareSheet = touch && navigator.share
      ? navigator.share({ text: text }).then(function () { return true; }, function (err) {
          return err && err.name === "AbortError";
        })
      : Promise.resolve(false);
    viaShareSheet.then(function (handled) {
      if (handled) return;
      var copy = navigator.clipboard && navigator.clipboard.writeText
        ? navigator.clipboard.writeText(text)
        : Promise.reject(new Error("no clipboard"));
      copy.then(function () { toast("تم نسخ النتيجة"); }, function () {
        var box = $("#share-fallback");
        var area = $("#share-text");
        area.value = text;
        box.hidden = false;
        area.focus();
        area.select();
      });
    });
  }

  // ---------- settings ----------
  function paintSettings() {
    $("#set-hard").setAttribute("aria-checked", String(settings.hardMode));
    $("#set-dark").setAttribute("aria-checked", String(isDark()));
    $("#set-contrast").setAttribute("aria-checked", String(settings.highContrast));
    $("#set-onscreen").setAttribute("aria-checked", String(settings.onscreenOnly));
  }

  function applyTheme() {
    var root = document.documentElement;
    if (settings.theme) root.setAttribute("data-theme", settings.theme);
    else root.removeAttribute("data-theme");
    root.classList.toggle("high-contrast", settings.highContrast);
  }

  function bindSettings() {
    $("#set-hard").addEventListener("click", function () {
      if (!settings.hardMode && game.status === "playing" && game.guesses.length > 0) {
        toast("لا يمكن تفعيل الوضع الصعب إلا في بداية الحزّورة");
        return;
      }
      settings.hardMode = !settings.hardMode;
      if (game.guesses.length === 0) game.hard = settings.hardMode;
      saveSettings();
      paintSettings();
    });
    $("#set-dark").addEventListener("click", function () {
      settings.theme = isDark() ? "light" : "dark";
      saveSettings();
      applyTheme();
      paintSettings();
    });
    $("#set-contrast").addEventListener("click", function () {
      settings.highContrast = !settings.highContrast;
      saveSettings();
      applyTheme();
      paintSettings();
    });
    $("#set-onscreen").addEventListener("click", function () {
      settings.onscreenOnly = !settings.onscreenOnly;
      saveSettings();
      paintSettings();
    });
  }

  // ---------- day rollover ----------
  function checkNewDay() {
    if (L.dayIndex(new Date()) === today || busy) return;
    closeSheet(true);
    loadDay();
    paintBoard();
    paintKeyboard();
    toast("حزّورة جديدة!");
  }

  // ---------- boot ----------
  function start(data) {
    loadDay();
    if (data && Array.isArray(data.current) && game.status === "playing") {
      current = data.current.filter(function (ch) { return L.LETTERS.indexOf(ch) !== -1; }).slice(0, L.WORD_LENGTH);
    }
    applyTheme();
    buildBoard();
    buildKeyboard();
    paintBoard();
    paintKeyboard();
    paintSettings();
    bindSettings();
    fitBoard();

    keyboardEl.addEventListener("click", onKeyboardClick);
    document.addEventListener("keydown", onKeyDown);
    $("#btn-help").addEventListener("click", function (e) { openModal("modal-help", e.currentTarget); });
    $("#btn-stats").addEventListener("click", function (e) { openStats(e.currentTarget); });
    $("#btn-settings").addEventListener("click", function (e) {
      paintSettings();
      openModal("modal-settings", e.currentTarget);
    });
    $("#btn-share").addEventListener("click", shareResult);
    document.querySelectorAll("[data-close]").forEach(function (btn) {
      btn.addEventListener("click", function () { closeSheet(); });
    });
    document.querySelectorAll(".overlay").forEach(function (overlay) {
      overlay.addEventListener("click", function (e) { if (e.target === overlay) closeSheet(); });
    });
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", paintSettings);
    if ("ResizeObserver" in window) new ResizeObserver(fitBoard).observe($("#board-wrap"));
    else window.addEventListener("resize", fitBoard);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) checkNewDay();
    });
    window.addEventListener("focus", checkNewDay);

    if (!storage.get("seenHelp", false) && stats.played === 0 && game.guesses.length === 0) {
      openModal("modal-help");
    } else if (game.status !== "playing") {
      later(openStats, 600);
    }
  }

  // Keep a half-typed row across live updates of the page.
  var hot = window.claude && window.claude.hot;
  if (hot && typeof hot.snapshot === "function") {
    hot.snapshot(function () { return { current: current.slice() }; });
  }
  if (hot && typeof hot.ready === "function") hot.ready(start);
  else start((hot && hot.data) || {});
})();
