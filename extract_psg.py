import datetime
import json
import logging
import os
import re
from glob import glob
from pathlib import Path

import hydra
import psg_utils.io.header.header_extractors as header_extractors
import psg_utils.io.psg.psg_extractors as psg_extractors
from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf
from psg_utils.errors import ChannelNotFoundError
from psg_utils.io import to_h5_file
from psg_utils.io.channels import ChannelMontageTuple, ChannelMontageCreator
from psg_utils.io.header import extract_header
from psg_utils.io.high_level_file_loaders import load_psg

from utils.extract_psg_utils import extract_from_rec

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def setup_extractors():
    header_extractors._EXT_TO_LOADER["rec"] = extract_from_rec(
        header_extractors.extract_edf_header
    )
    psg_extractors._EXT_TO_LOADER["rec"] = extract_from_rec(
        psg_extractors.extract_from_edf
    )


def filter_channels(renamed_channels, selected_original_channels, original_channels):
    return [
        chan
        for i, chan in enumerate(renamed_channels)
        if original_channels[i] in selected_original_channels
    ]


def find_duplicate_channels(channels):
    duplicate_channels = []
    ref_channels = ChannelMontageTuple(channels, relax=True)
    channels = ChannelMontageTuple(channels, relax=True)
    for channel in channels:
        if ref_channels.count(channel) > 1:
            duplicate_channels.append(channel.original_name)
    return list(set(duplicate_channels))


def standard_extract(
    psg_file, out_path, channels, renamed_channels, write_offsets_to_file
):
    channels_in_file = extract_header(psg_file)["channel_names"]
    duplicate_channels = find_duplicate_channels(channels_in_file)
    if duplicate_channels:
        logger.info(
            f"[*] Duplicate channels found: {duplicate_channels}, removing all instances"
        )
        channels_in_file = [
            chan for chan in channels_in_file if chan not in duplicate_channels
        ]

    chan_creator = ChannelMontageCreator(
        existing_channels=channels_in_file,
        channels_required=channels,
        allow_missing=True,
    )
    logger.info(
        f"[*] Channels in file: {', '.join(chan_creator.existing_channels.names)}"
    )
    logger.info(f"[*] Output channels: {', '.join(chan_creator.output_channels.names)}")
    logger.info(
        f"[*] Channels to load: {', '.join(chan_creator.channels_to_load.names)}"
    )
    try:
        psg, header = load_psg(
            psg_file,
            load_channels=chan_creator.channels_to_load,
            allow_missing_channels=True,
        )
    except ChannelNotFoundError as e:
        raise ValueError(
            f"\n-----\n" f"CHANNEL ERROR ON FILE {psg_file}\n" f"{str(e)}\n" f"-----"
        )

    # clean up offsets
    if write_offsets_to_file:
        offsets_file = Path(out_path).parents[1] / "preparations" / "offsets.json"
        offsets = json.load(open(str(offsets_file)))
        subj_id = Path(out_path).stem
        if not subj_id in offsets:
            raise ValueError(f"Could not find offsets for {subj_id}")
        subj_offset = offsets[subj_id]
        logger.info(f"[*] Removing offset of {subj_offset} seconds")
        psg = psg[subj_offset * header["sample_rate"] :]
        header["date"] = header["date"] + datetime.timedelta(seconds=subj_offset)

    # create montages
    psg, final_channels = chan_creator.create_montages(psg)
    header["channel_names"] = final_channels
    logger.info(f"[*] Original PSG shape: {psg.shape}")

    if psg.shape[0] % header["sample_rate"]:
        logger.info(
            f"--- OBS: Length {len(psg)} not divisible by sample rate! "
            f"Trimming N items from end {len(psg) % header['sample_rate']}."
        )
        psg = psg[: -(psg.shape[0] % header["sample_rate"])]
        logger.info(f"--- New PSG shape: {psg.shape}")

    # Rename channels
    if renamed_channels:
        selected_orig_channels = header["channel_names"].original_names
        header["channel_names"] = filter_channels(
            renamed_channels, selected_orig_channels, channels.original_names
        )
    else:
        header["channel_names"] = header["channel_names"].original_names
    logger.info(f"[*] Extracted {psg.shape[1]} channels: {header['channel_names']}")
    to_h5_file(out_path, psg, **header)


@hydra.main(config_path="./config", version_base="1.2")
def main(cfg: DictConfig):
    hydra_cfg = HydraConfig.get()
    logger.info(f"overrides:\n{OmegaConf.to_yaml(hydra_cfg.overrides)}")

    out_dir = os.path.join(cfg.general.save_dir, cfg.name)
    file_regex = os.path.join(cfg.general.base_dir, cfg.psg.file_glob)
    use_dir_names = cfg.use_dir_names
    extractor = cfg.psg.extractor
    channels = (
        list(cfg.psg.eeg_channels)
        + list(cfg.psg.eog_channels)
        + list(cfg.psg.emg_channels)
    )
    renamed_channels = (
        list(cfg.psg.renamed_eeg_channels)
        if cfg.psg.renamed_eeg_channels
        else list(cfg.psg.eeg_channels)
    )
    renamed_channels += (
        list(cfg.psg.renamed_eog_channels)
        if cfg.psg.renamed_eog_channels
        else list(cfg.psg.eog_channels)
    )
    renamed_channels += (
        list(cfg.psg.renamed_emg_channels)
        if cfg.psg.renamed_emg_channels
        else list(cfg.psg.emg_channels)
    )

    files = glob(file_regex)
    out_dir = os.path.abspath(out_dir)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    logger.info(f"Found {len(files)} files matching glob statement")
    if len(files) == 0:
        return

    channels = ChannelMontageTuple(channels, relax=True)
    if renamed_channels and (len(renamed_channels) != len(channels)):
        raise ValueError(
            "renamed_channels argument must have the same number"
            " of elements as channels. Got {} and {}.".format(
                len(channels), len(renamed_channels)
            )
        )

    logger.info(f"Extracting channels {channels.names}")
    logger.info(
        (f"Saving channels under names {renamed_channels}" if renamed_channels else "")
    )
    logger.info(f"Saving .h5 files to '{out_dir}'")
    logger.info("-*--*--*--*--*--*--*--*--*--*--*--*--*--*--*--*-")

    # adding custom extractors
    setup_extractors()

    for i, file_ in enumerate(files):
        if use_dir_names is False:
            name = os.path.splitext(os.path.split(file_)[-1])[0]
        elif use_dir_names is True:
            name = os.path.split(os.path.split(file_)[0])[-1]
        else:
            name = "_".join(file_.split(os.path.sep)[use_dir_names - 1 : -1])
        name = re.sub(cfg.psg.id_regex, "\g<1>", name)
        logger.info("------------------")
        logger.info(f"[*] {i+1}/{len(files)} Processing {name}")
        out_dir_subject = os.path.join(out_dir, name)
        if not os.path.exists(out_dir_subject):
            os.mkdir(out_dir_subject)
        out_path = os.path.join(out_dir_subject, name + ".h5")
        if os.path.exists(out_path):
            raise OSError(f"File already exists at '{out_path}'")
        instantiate(
            extractor,
            psg_file=file_,
            out_path=out_path,
            channels=channels,
            renamed_channels=renamed_channels,
            write_offsets_to_file=cfg.hypno.write_offsets_to_file,
        )


if __name__ == "__main__":
    main()
