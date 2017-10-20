#!/bin/bash

set -e

mkdir -p backgrounds
cd backgrounds
for f in `cat ../inventory_backgrounds.txt`; do
  v=`echo $f | sed "s/.*watch.v=//"`
  target="audio_$v.m4a"
  wav="audio_$v.wav"
  echo $f $target
  if [ ! -e $target ]; then
    src=`youtube-dl -f 140 --get-url "$f"`
	  let secs=30*60
  	ffmpeg -ss 60 -i "$src" -t $secs -c:a copy $target
  fi
  if [ ! -e $wav ]; then
  	ffmpeg -loglevel panic -i $target -c:a pcm_s16le -ar 16000 -ac 1 $wav
  fi
done
cd ..

python prep/main.py inventory
