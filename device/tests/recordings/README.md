# Real recordings

Recordings made at the mirror, replayed by `test_recordings.py` on every test
run. They catch changes that pass the synthetic tests but break counting for a
real person in front of a real camera.

## Adding one

1. Record a set (or a few sets with rests between them):

   ```
   python -m easyweight --record tests/recordings/curls_10.jsonl.gz
   ```

2. Check what it counts:

   ```
   python -m easyweight.replay tests/recordings/curls_10.jsonl.gz
   ```

3. If that matches what you actually did, write it into the recording's first
   line as `"expected"`, so the test knows the right answer. The first line of
   the (unzipped) file then looks like:

   ```json
   {"format":"easyweight-recording","version":1,"width":1280,"height":720,"model":"full","expected":[{"exercise":"curl","set":1,"reps":10}]}
   ```

   If it doesn't match, that's a bug to fix: keep the recording, write in what
   you really did, and the test will fail until the counting is fixed.

Keep recordings short (under a minute, gzipped), so the repository stays small.
