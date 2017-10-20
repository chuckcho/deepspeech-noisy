#!/usr/bin/env python

import argparse
from collections import defaultdict
from prep.parameters import *
import glob
import json
import numpy as np
import os
import random
import shutil
import time
from tqdm import tqdm

def make_voice_inventory():
    audios = glob.glob('voices/*/*/*/*/*/*.wav')
    audios.sort()
    voices = defaultdict(list)
    for audio in audios:
        person = os.path.split(audio)[0]
        person = os.path.split(person)[0]
        person = os.path.split(person)[-1]
        voices[int(person)].append(audio)
    keys = sorted(voices.keys())
    stats = { 'voice': audios }
    fname = 'all_voices.json'
    with open(fname, 'w') as fout:
        json.dump(stats, fout, indent=2)
    print('Generated {}'.format(fname))

def make_background_inventory():
    audios = glob.glob('backgrounds/*.wav')
    audios.sort()
    stats = [{
        'sample': audio
    } for audio in audios]
    fname = 'all_backgrounds.json'
    with open(fname, 'w') as fout:
        json.dump(stats, fout, indent=2)
    print('Generated {}'.format(fname))

def pick(options):
    assert(abs(np.sum(o[0] for o in options) - 1.0) < 1e-6)
    x = random.random()
    for i, option in enumerate(options):
        x -= option[0]
        if x < 0:
            return option[1]
    return options[-1][1]

def apply_mask(mask, seq):
    idx = [(i % len(mask)) for i in range(0, len(seq))]
    seq = [s for i, s in zip(idx, seq) if mask[i] == 'x']
    return seq

def make_samples(target, mask, seed):
    # make data generation reproducible
    print "Using random seed={}".format(seed)
    random.seed(seed)

    from scipy.io import wavfile
    if os.path.exists(target):
        shutil.rmtree(target)
    os.makedirs(target)

    all_backgrounds = apply_mask(mask, all_backgrounds)

    all_voices = json.load(open('all_voices.json'))['voice']
    all_voices = apply_mask(mask, all_voices)

    background_cache = {}
    rate = SAMPLE_RATE
    inventory = []

    # how often do we pad (either at start or at end wiht 1/2 prob)
    padding_rate = 0.1

    try:
        for k in tqdm(range(len(all_voices))):
            # read foreground audio

            irate, speech = wavfile.read(all_voices[k])
            assert(rate == irate)
            samples = len(speech)
            duration = float(samples) / rate

            # decide about padding
            start = 0.0
            stop = duration
            if random.random() < padding_rate:
                # yes, we will have padding at start. how long?
                pad_at_start = random.uniform(0.0, duration * 0.2)
            else:
                pad_at_start = 0.0

            if random.random() < padding_rate:
                # yes, we will have padding at end. how long?
                pad_at_end = random.uniform(0.0, duration * 0.2)
            else:
                pad_at_end = 0.01

            total_duration = duration + pad_at_start + pad_at_end
            total_samples = int(total_duration * rate)

            # pick background audio
            number_of_backgrounds = pick([(0.2, 0),
                                          (0.8, 1)])
            backgrounds = []
            background_index = random.sample(range(0, len(all_backgrounds)),
                                             number_of_backgrounds)
            for i in background_index:
                if i not in background_cache:
                    background_cache[i] = wavfile.read(all_backgrounds[i]
                                                       ['sample'])
                irate, background = background_cache[i]
                assert(rate == irate)
                offset = random.randint(0, len(background) - total_samples)
                backgrounds.append(background[offset:(offset + total_samples)])

            # finally ready to pull together a waveform
            audio = np.zeros((total_samples,), dtype=np.float)
            scales = []
            for background in backgrounds:
                scale = random.uniform(0.3, 0.6)
                audio += background * scale
                scales.append(scale)

            scale = random.uniform(0.6, 1.0)
            offset = int(pad_at_start * rate)
            #print "offset={}".format(offset)
            #print "len(speech)={}".format(len(speech))
            #print "scale={}".format(scale)
            #print "len(audio[offset:(offset+len(speech)))={}".format(len(audio[offset:(offset+len(speech))]))
            audio[offset:(offset + len(speech))] += speech * scale
            scales.append(scale)
            layout = {
                'speech duration': duration,
                'total duration': total_duration,
                'start': pad_at_start,
                'stop': pad_at_start + duration,
            }

            if len(scales) > 0:
                audio /= np.sum(scales)
            audio = audio.astype(np.int16)

            # done! save
            out_wave_fname = os.path.join(target, '%06d.wav' % k)
            wavfile.write(out_wave_fname, rate, audio)
            inventory.append({
                'n': k,
                'audio': out_wave_fname,
                'wav': all_voices[k],
                'layout': layout
            })
    finally:
        data = {
            'samples': inventory
        }
        fname = os.path.join(target, 'index.json')
        with open(fname, 'w') as fout:
            json.dump(data, fout, indent=2)

        cwd = os.path.dirname(os.path.realpath(__file__))
        fname = os.path.join(target, 'inventory.csv')
        with open(fname, 'w') as fout:
            fout.write('wav_filename,wav_filesize,transcript\n')
            transcript_cache = {}
            for inv in inventory:
                wav_file = os.path.realpath(inv['audio'])
                assert os.path.exists(wav_file), "wav_file={} doesn't exist!".format(wav_file)
                filesize = os.path.getsize(wav_file)
                transcript_path = os.path.dirname(os.path.realpath(
                        os.path.join(cwd, '..', inv['wav'])))
                voice_id = os.path.splitext(os.path.basename(inv['wav']))[0]
                reader_id, chapter_id = voice_id.split('-')[:2]
                rc_id = '{}-{}'.format(reader_id, chapter_id)
                transcript_file = os.path.join(transcript_path, '{}.trans.txt'.format(rc_id))
                if rc_id not in transcript_cache:
                    with open(transcript_file, 'r') as f:
                        transcript_cache[rc_id] = f.readlines()
                transcript = [t for t in transcript_cache[rc_id] if t.startswith(voice_id)][0].rstrip('\n').lower().replace(voice_id+' ','').replace(',','')

                fout.write('{},{},{}\n'.format(
                        wav_file,
                        filesize,
                        transcript,
                        ))
        print("Wrote to {}".format(target))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='subcommands',
                                       dest='subcommand')
    subparsers.add_parser('inventory')
    generate = subparsers.add_parser('generate')
    generate.add_argument('directory')
    generate.add_argument('--seed', default=9257042)
    generate.add_argument('mask', help='something like xoo for split 1 of 3, '
                     'oxxx for splits 2-4 of 4')
    sample = subparsers.add_parser('sample')
    sample.add_argument('directory')
    args = parser.parse_args()
    if args.subcommand == 'inventory':
        make_voice_inventory()
        make_background_inventory()
    elif args.subcommand == 'generate':
        make_samples(args.directory, args.mask, args.seed)
