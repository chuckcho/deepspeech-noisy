DeepSpeech experiments stub.

Contains:

 * A script to download voice samples from http://www.openslr.org/12/
 * A script to download background audio from youtube.
 * A script to generate labeled voice-with-background samples.

To use, make sure you've > 150GB free and plenty of time,
and run:

```
export PYTHONPATH=$PWD:$PYTHONPATH
./download_voices.sh
./download_backgrounds.sh
python prep/main.py generate train xxxoo
python prep/main.py generate dev oooxo
python prep/main.py generate test  oooox
```

Then, run mozilla/DeepSpeech training script
