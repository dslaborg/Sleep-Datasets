import json
import logging
import os
import tempfile

import h5py
import numpy as np
from psg_utils.io import to_h5_file

logger = logging.getLogger(__name__)


def extract_from_rec(func):
    def extractor(file_path, **args):
        # create tempfile from file_path with edf extension instead of rec extension
        temp_file_path = tempfile.mktemp(suffix=".edf")
        os.symlink(file_path, temp_file_path)
        # extract header from temp file
        data = func(temp_file_path, **args)
        # delete temp file
        os.remove(temp_file_path)
        return data

    return extractor


def dod_extract(psg_file, out_path, channels, renamed_channels, **kwargs):
    with h5py.File(psg_file, "r") as in_f:
        description = json.loads(in_f.attrs["description"])
        channel_names_descr = [c["path"].split("/")[-1] for c in description]

        logger.info(f"[*] Channels in file: {', '.join(channel_names_descr)}")
        logger.info(f"[*] Channels to load: {', '.join(channels.original_names)}")

        data = []
        sample_rates = []
        channel_names = []
        for i, channel in enumerate(channels):
            if channel.original_name in channel_names_descr:
                channel_name = (
                    channel.original_name
                    if not renamed_channels
                    else renamed_channels[i]
                )
                h5_channel = description[
                    channel_names_descr.index(channel.original_name)
                ]
                sample_rates.append(int(h5_channel["fs"]))
                data.append(np.array(in_f[h5_channel["path"]]))
                channel_names.append(channel_name)

        assert np.all(np.array(sample_rates) == sample_rates[0])
        logger.info(f"[*] Extracted {len(data)} channels: {channel_names}")

        to_h5_file(
            out_path=out_path,
            data=np.array(data).T,
            sample_rate=sample_rates[0],
            channel_names=channel_names,
            date=None,
        )
