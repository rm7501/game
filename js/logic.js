// Pure game rules: no DOM, so the same file runs in the browser and in Node tests.
(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.HZLogic = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var WORD_LENGTH = 5;
  var MAX_GUESSES = 6;
  // 28 letters of the alphabet plus taa marbuta, alef maqsura and the hamza forms
  // that have their own key. Alef with hamza/madda folds into plain alef.
  var LETTERS = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي" + "ةىءؤئ";
  var LETTER_SET = new Set(Array.from(LETTERS));
  var DIACRITICS = /[ً-ٰٟـ]/g;
  var ALEF_FORMS = /[أإآٱ]/g;
  // Puzzle #1 is the first day the game went live (local calendar date).
  var EPOCH = { year: 2026, month: 9, day: 16 };
  var DAY_MS = 86400000;

  function normalizeWord(text) {
    return String(text).replace(DIACRITICS, "").replace(ALEF_FORMS, "ا");
  }

  // Turns raw key input ("أ", "لا", "ـبـ") into playable letters; drops anything else.
  function lettersFromInput(text) {
    return Array.from(normalizeWord(text)).filter(function (ch) {
      return LETTER_SET.has(ch);
    });
  }

  function isWellFormed(word) {
    var letters = Array.from(word);
    return letters.length === WORD_LENGTH && letters.every(function (ch) {
      return LETTER_SET.has(ch);
    });
  }

  // Classic two-pass scoring so repeated letters are only marked as often as
  // they occur in the answer: exact matches first, then misplaced ones.
  function evaluateGuess(guess, answer) {
    var g = Array.from(guess);
    var a = Array.from(answer);
    var result = new Array(g.length).fill("absent");
    var remaining = {};
    for (var i = 0; i < g.length; i++) {
      if (g[i] === a[i]) result[i] = "correct";
      else remaining[a[i]] = (remaining[a[i]] || 0) + 1;
    }
    for (var j = 0; j < g.length; j++) {
      if (result[j] !== "correct" && remaining[g[j]] > 0) {
        result[j] = "present";
        remaining[g[j]]--;
      }
    }
    return result;
  }

  // Hard mode: every revealed hint has to be reused. Returns the first broken
  // rule, or null when the guess is allowed.
  function hardModeViolation(guess, history) {
    var g = Array.from(guess);
    for (var r = 0; r < history.length; r++) {
      var prev = Array.from(history[r].guess);
      var res = history[r].result;
      for (var i = 0; i < prev.length; i++) {
        if (res[i] === "correct" && g[i] !== prev[i]) {
          return { type: "position", index: i, letter: prev[i] };
        }
      }
      var needed = {};
      for (var k = 0; k < prev.length; k++) {
        if (res[k] !== "absent") needed[prev[k]] = (needed[prev[k]] || 0) + 1;
      }
      for (var letter in needed) {
        var have = g.filter(function (ch) { return ch === letter; }).length;
        if (have < needed[letter]) return { type: "include", letter: letter };
      }
    }
    return null;
  }

  // Best state seen for each letter, for colouring the on-screen keyboard.
  var RANK = { absent: 1, present: 2, correct: 3 };
  function keyboardStates(history) {
    var states = {};
    history.forEach(function (row) {
      Array.from(row.guess).forEach(function (ch, i) {
        var s = row.result[i];
        if (!states[ch] || RANK[s] > RANK[states[ch]]) states[ch] = s;
      });
    });
    return states;
  }

  function dayIndex(date) {
    var today = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate());
    var start = Date.UTC(EPOCH.year, EPOCH.month, EPOCH.day);
    return Math.round((today - start) / DAY_MS);
  }

  function answerForDay(index, answers) {
    var n = answers.length;
    return answers[((index % n) + n) % n];
  }

  function msUntilNextDay(date) {
    var next = new Date(date.getFullYear(), date.getMonth(), date.getDate() + 1);
    return next.getTime() - date.getTime();
  }

  function emptyStats() {
    return {
      played: 0,
      wins: 0,
      currentStreak: 0,
      maxStreak: 0,
      distribution: [0, 0, 0, 0, 0, 0],
      lastPlayedDay: null,
      lastWonDay: null
    };
  }

  // A streak survives only if yesterday's puzzle (or today's) was won.
  function refreshStreak(stats, today) {
    if (stats.currentStreak > 0 && stats.lastWonDay !== null && stats.lastWonDay < today - 1) {
      stats.currentStreak = 0;
    }
    return stats;
  }

  function recordResult(stats, day, won, guessCount) {
    if (stats.lastPlayedDay === day) return stats; // already counted
    stats.played += 1;
    stats.lastPlayedDay = day;
    if (won) {
      stats.wins += 1;
      stats.distribution[guessCount - 1] += 1;
      stats.currentStreak = stats.lastWonDay === day - 1 ? stats.currentStreak + 1 : 1;
      stats.lastWonDay = day;
      stats.maxStreak = Math.max(stats.maxStreak, stats.currentStreak);
    } else {
      stats.currentStreak = 0;
    }
    return stats;
  }

  var ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";
  function toArabicDigits(value) {
    return String(value).replace(/[0-9]/g, function (d) { return ARABIC_DIGITS[d]; });
  }

  var SQUARES = {
    normal: { correct: "🟩", present: "🟨" },
    contrast: { correct: "🟧", present: "🟦" }
  };
  // Emoji grid for sharing. Each row starts with a right-to-left mark so it
  // reads right to left like the board, whatever app it is pasted into.
  function shareText(opts) {
    var palette = opts.highContrast ? SQUARES.contrast : SQUARES.normal;
    var blank = opts.dark ? "⬛" : "⬜";
    var score = opts.won ? toArabicDigits(opts.results.length) : "X";
    var header = opts.title + " " + toArabicDigits(opts.number) + " " + score + "/" +
      toArabicDigits(MAX_GUESSES) + (opts.hardMode ? "*" : "");
    var rows = opts.results.map(function (result) {
      return "‏" + result.map(function (s) {
        return s === "absent" ? blank : palette[s];
      }).join("");
    });
    return [header, ""].concat(rows).join("\n");
  }

  return {
    WORD_LENGTH: WORD_LENGTH,
    MAX_GUESSES: MAX_GUESSES,
    LETTERS: LETTERS,
    normalizeWord: normalizeWord,
    lettersFromInput: lettersFromInput,
    isWellFormed: isWellFormed,
    evaluateGuess: evaluateGuess,
    hardModeViolation: hardModeViolation,
    keyboardStates: keyboardStates,
    dayIndex: dayIndex,
    answerForDay: answerForDay,
    msUntilNextDay: msUntilNextDay,
    emptyStats: emptyStats,
    refreshStreak: refreshStreak,
    recordResult: recordResult,
    toArabicDigits: toArabicDigits,
    shareText: shareText
  };
});
