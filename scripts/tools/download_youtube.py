import argparse
import glob
import os
import string
import subprocess
from collections import Counter

import yaml

from tools.build_data import create_csv

file_counter = Counter()


def read_yaml(file_name):
    """
    Read the YAML file
    :param file_name: file to be read
    :return: loaded yaml file
    """
    with open(file_name, "r") as f:
        return yaml.load(f)


def clean_filename(filename):
    """
    Clean file names to remove redundant characters before storing data in CSV
    :param filename: file name to be cleaned
    :return: cleaned file name
    """
    valid_chars = "-_%s%s" % (string.ascii_letters, string.digits)
    new_name = "".join(c for c in filename if c in valid_chars)
    new_name = new_name.replace(' ', '_')
    return new_name


def download(language, source, source_name, source_type):
    """
    Download video/s from YouTube
    :param language: language of the YouTube video
    :param source: user
    :param source_name: name of the source
    :param source_type: whether the YouTube source is a channel or playlist
    :return: void
    """
    output_path_raw = os.path.join(args.output_path, "raw", language, source_name)

    if source_type == "playlist":
        playlist_archive = os.path.join(output_path_raw, "archive.txt")

        print("Downloading {0} {1} to {2}".format(source_type, source_name, output_path_raw))
        command = """youtube-dl -i --download-archive {} --max-filesize 50m --no-post-overwrites --max-downloads {} \
        --extract-audio --audio-format wav {} -o "{}/%(title)s.%(ext)s" """.format(
            playlist_archive, args.max_downloads, source, output_path_raw)
        subprocess.call(command, shell=True)

    else:
        if os.path.exists(output_path_raw):
            print("skipping {0} because the target folder already exists".format(output_path_raw))
        else:
            print("Downloading {0} {1} to {2}".format(source_type, source_name, output_path_raw))
            command = """youtube-dl -i --max-downloads {} --extract-audio --audio-format wav {} \
            -o "{}/%(title)s.%(ext)s" """.format(args.max_downloads, source, output_path_raw)
            subprocess.call(command, shell=True)

    # Use ffmpeg to convert and split WAV files into 10 second parts
    output_path_segmented = os.path.join(
        args.output_path, "segmented", language, source_name)  # split WAV files stored in 'segmented' folder
    segmented_files = glob.glob(os.path.join(output_path_segmented, "*.wav"))

    if source_type == "playlist" or not os.path.exists(output_path_segmented):
        if not os.path.exists(output_path_segmented):
            os.makedirs(output_path_segmented)

        files = glob.glob(os.path.join(output_path_raw, "*.wav"))

        for f in files:
            cleaned_filename = clean_filename(os.path.basename(f))
            cleaned_filename = cleaned_filename[:-4]

            if source_type == "playlist":
                waves = [f for f in segmented_files if cleaned_filename in f]
                if len(waves) > 0:
                    continue

            output_filename = os.path.join(output_path_segmented, cleaned_filename + "_%03d.wav")

            command = ["ffmpeg", "-y", "-i", f, "-map", "0", "-ac", "1", "-ar", "16000", "-f", "segment",
                       "-segment_time", "10", output_filename]
            subprocess.call(command)

    file_counter[language] += len(glob.glob(os.path.join(output_path_segmented, "*.wav")))


def download_user(language, user):
    user_selector = "ytuser:%s" % user
    download(language, user_selector, user, "user")


def download_playlist(language, playlist_name, playlist_id):
    download(language, playlist_id, playlist_name, "playlist")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', dest='output_path', default=os.getcwd(), required=True)
    parser.add_argument('--downloads', dest='max_downloads', default=1200)
    args = parser.parse_args()

    sources = read_yaml("config/sources.yml")
    for language, categories in sources.items():
        for user in categories["users"]:
            if user is None:
                continue

            download_user(language, user)

        for category in categories["playlists"]:
            if category is None:
                continue

            playlist_name = category
            playlist_id = category
            download_playlist(language, playlist_name, playlist_id)

    create_csv(os.path.join(args.output_path, "segmented"))

    print(file_counter)


# REFERENCES:
# Bartz, C., Herold, T., Yang, H., and Meinel, C.: ‘Language identification using deep convolutional recurrent neural
# networks’, in Editor (Ed.)^(Eds.): ‘Book Language identification using deep convolutional recurrent neural networks’
# (Springer, 2017, edn.), pp. 880-889 https://arxiv.org/pdf/1708.04811v1.pdf
