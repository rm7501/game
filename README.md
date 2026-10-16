# حزّورة — Hazzoora

A daily Arabic word-guessing game: guess the five-letter word of the day in six tries.
Green means the letter is in the right place, gold means it is in the word but somewhere
else, and grey means it is not in the word.

This is an original, from-scratch implementation of the daily word-guessing format popularised
by Wordle. It contains no code, artwork, word lists, or branding from The New York Times and is
not affiliated with it.

## Play

Open `index.html` in a browser, or serve the folder with any static host (GitHub Pages works
as-is). To run it locally:

```sh
python3 -m http.server 8000
# then visit http://localhost:8000
```

## What's in it

- Right-to-left 6 × 5 board with flip, pop, shake and win animations
- On-screen Arabic keyboard (33 keys), plus physical keyboard input. Both Arabic layouts and
  English layouts work; English keys are mapped by the position of the matching Arabic letter.
- A new word every day at local midnight, with progress saved in the browser
- Statistics: games played, win %, current and longest streak, guess distribution, a countdown
  to the next puzzle, and today's date in the Hijri (Umm al-Qura) calendar
- Share button: copies an emoji grid that reads right to left
- Settings: hard mode, dark theme, high-contrast colours, on-screen keyboard only

### Arabic letter rules

- أ, إ, آ are all entered as ا.
- ة, ى, ء, ؤ and ئ are separate letters, each with its own key.
- Diacritics are ignored.

## Project layout

| Path | Purpose |
| --- | --- |
| `index.html` | Page markup: board, keyboard, help, statistics and settings sheets |
| `css/style.css` | Styles and themes (light, dark, high contrast) |
| `js/logic.js` | Game rules with no DOM code: scoring, hard mode, dates, streaks, share text |
| `js/app.js` | UI: rendering, input, animations, persistence |
| `js/words.js` | Daily answers (406 curated common words) in schedule order |
| `js/valid-words.js` | Accepted guesses (~46k words), generated |
| `tools/build_valid_words.py` | Rebuilds `valid-words.js` from the frequency list |
| `tests/logic.test.js` | Unit tests: `node --test tests/logic.test.js` |

To add answers, append them to the end of `js/words.js` so past puzzles keep their words.

## Credits

The accepted-guess dictionary (`js/valid-words.js`) is derived from
[FrequencyWords](https://github.com/hermitdave/FrequencyWords) by Hermit Dave (OpenSubtitles 2018),
licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The filtered list is
shared under the same licence.
