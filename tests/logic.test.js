// Run with: node --test tests/
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../js/logic.js");
const ANSWERS = require("../js/words.js");
const VALID = require("../js/valid-words.js");

test("normalizes alef with hamza or madda and strips diacritics", () => {
  assert.equal(L.normalizeWord("أمطار"), "امطار");
  assert.equal(L.normalizeWord("إبريق"), "ابريق");
  assert.equal(L.normalizeWord("مُدَرِّسة"), "مدرسة");
  assert.deepEqual(L.lettersFromInput("لا"), ["ل", "ا"]);
  assert.deepEqual(L.lettersFromInput("q"), []);
});

test("scores exact, misplaced and missing letters", () => {
  assert.deepEqual(L.evaluateGuess("مدرسة", "مدرسة"), Array(5).fill("correct"));
  // ح and ة are right, ي and ق swapped places, د is not in the answer.
  assert.deepEqual(
    L.evaluateGuess("حقيدة", "حديقة"),
    ["correct", "present", "correct", "present", "correct"]
  );
});

test("repeated letters are marked no more often than the answer has them", () => {
  // answer has one م at index 0
  assert.deepEqual(
    L.evaluateGuess("ممحاة", "مدرسة"),
    ["correct", "absent", "absent", "absent", "correct"]
  );
  // answer ملعقة has one م; guess has م twice, neither in place
  assert.deepEqual(
    L.evaluateGuess("سممرة", "ملعقة"),
    ["absent", "present", "absent", "absent", "correct"]
  );
  // answer جمجمة has ج twice; guess places one correctly, one elsewhere
  assert.deepEqual(
    L.evaluateGuess("جاجةج", "جمجمة"),
    ["correct", "absent", "correct", "present", "absent"]
  );
});

test("hard mode demands revealed letters", () => {
  const history = [{ guess: "سيارة", result: L.evaluateGuess("سيارة", "سفينة") }];
  assert.deepEqual(L.hardModeViolation("مدرسة", history), { type: "position", index: 0, letter: "س" });
  assert.deepEqual(L.hardModeViolation("سفارة", history), { type: "include", letter: "ي" });
  assert.equal(L.hardModeViolation("سفينة", history), null);
});

test("keyboard keeps the best state per letter", () => {
  const history = [
    { guess: "سيارة", result: ["absent", "present", "absent", "absent", "correct"] },
    { guess: "يمامة", result: ["correct", "absent", "absent", "absent", "correct"] }
  ];
  const k = L.keyboardStates(history);
  assert.equal(k["ي"], "correct");
  assert.equal(k["س"], "absent");
  assert.equal(k["ة"], "correct");
});

test("days count local calendar dates from the first puzzle", () => {
  assert.equal(L.dayIndex(new Date(2026, 9, 16, 0, 5)), 0);
  assert.equal(L.dayIndex(new Date(2026, 9, 16, 23, 59)), 0);
  assert.equal(L.dayIndex(new Date(2026, 9, 17, 0, 0)), 1);
  assert.equal(L.dayIndex(new Date(2027, 2, 30, 12)), 165); // across a DST change
  assert.equal(L.answerForDay(-1, ["a", "b", "c"]), "c");
  assert.equal(L.answerForDay(4, ["a", "b", "c"]), "b");
});

test("streaks grow on consecutive wins and reset on a loss or a missed day", () => {
  let s = L.emptyStats();
  L.recordResult(s, 10, true, 3);
  L.recordResult(s, 11, true, 4);
  assert.equal(s.currentStreak, 2);
  L.recordResult(s, 11, true, 4); // same day is ignored
  assert.equal(s.played, 2);
  L.recordResult(s, 12, false, 6);
  assert.equal(s.currentStreak, 0);
  assert.equal(s.maxStreak, 2);
  L.recordResult(s, 13, true, 1);
  L.refreshStreak(s, 15);
  assert.equal(s.currentStreak, 0);
  assert.deepEqual(s.distribution, [1, 0, 1, 1, 0, 0]);
  assert.equal(s.wins, 3);
});

test("share text reads right to left with Arabic-Indic digits", () => {
  const text = L.shareText({
    title: "حزّورة", number: 12, won: true, hardMode: true, highContrast: false, dark: false,
    results: [["absent", "present", "absent", "absent", "correct"], Array(5).fill("correct")]
  });
  assert.equal(text, "حزّورة ١٢ ٢/٦*\n\n‏⬜🟨⬜⬜🟩\n‏🟩🟩🟩🟩🟩");
});

test("answers are unique, well-formed words and the dictionary is clean", () => {
  const valid = new Set(VALID);
  const keys = ANSWERS.map(L.normalizeWord);
  assert.equal(new Set(keys).size, keys.length, "duplicate answers");
  for (const k of keys) {
    assert.ok(L.isWellFormed(k), `malformed answer ${k}`);
  }
  assert.ok(ANSWERS.length >= 365);
  assert.ok(VALID.every(L.isWellFormed));
  assert.ok(valid.size > 40000);
});
