# Taking part and contributing

## Adding your row

1. Build the club and its observer in your own public repository, following [RULES.md](RULES.md). Start them.
2. From a checkout of this repository, check it:

   ```sh
   python3 check_bookclub/check_bookclub.py run --base-url http://127.0.0.1:8488 \
       --observer-url http://127.0.0.1:8489 --witness witness.json
   # stop your club, delete its read model, start it again
   python3 check_bookclub/check_bookclub.py recheck --base-url http://127.0.0.1:8488 --witness witness.json
   python3 stranger_test/stranger_test.py path/to/your/checkout
   ```

3. Put `witness.json` and your cost evidence in the `vibe/` folder of your repository and commit. That commit is the one you enter.
4. Fork this repository. Copy `entries/TEMPLATE.toml` to `entries/<your-handle>-<language>.toml` and fill it in.
5. Redraw the table: `python3 draw_table/draw_table.py`
6. Open a pull request with those two files: your entry and `TABLE.md`.

CI checks that your entry is well-formed and that the table matches the entries. A maintainer merges it. Nobody judges your code; your row says what the suite said.

You can enter the same club again after improving it: change the commit and the numbers in your file. You can enter a second club in another language: add a second file.

## Doubting a row

Clone the repository the row names, check out the commit, start the club, run the suite. If your result differs from the row, open an issue here that names the row and says what you ran and what you saw.

## Changing the assignment or the tools

The suite carries a version, and every row shows the version it was checked with. To change the assignment or a check, open an issue first. A change to a check needs a matching planted defect in `check_bookclub/model_club.py` and an expectation in `check_bookclub/test_check_bookclub.py`, so that the suite is shown to fail a club that gets it wrong.

Run everything CI runs before you push:

```sh
./check.sh
```

The lint floor has no exceptions: ruff's rules, cyclomatic complexity of at most 9, nesting of at most 3, and formatting, as set in `ruff.toml`.
