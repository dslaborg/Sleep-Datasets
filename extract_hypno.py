import json
import logging
import os
import re
from glob import glob

import hydra
import numpy as np
from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf
from psg_utils.hypnogram.utils import fill_hyp_gaps
from psg_utils.io.hypnogram import extract_ids_from_hyp_file

from utils.start_time_extractors import extract_start_time

logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def write_to_ids_file(start, durs, stage, out, stage_mapping, start_date):
    with open(out, "w") as out_f:
        for i, d, s in zip(start, durs, stage):
            mapped_s = stage_mapping[str(s)]
            out_f.write("{},{},{}\n".format(int(i), int(d), mapped_s))


def remove_offset(inits):
    offset = inits[0]
    new_inits = []
    for i in range(len(inits)):
        new_init = inits[i] - offset
        rounded_new_init = np.round(new_init)
        if new_init - rounded_new_init > 1e-6:
            raise ValueError(
                f"Unexpectedly large difference of {new_init - rounded_new_init} between new_init of "
                f"{new_init} and round(new_init) of {rounded_new_init} when "
                "removing offset. The implementation expects inits to land on whole-seconds, not "
                "fractions."
            )
        new_inits.append(new_init)
    return new_inits


def fill_offset(inits: tuple, durs: tuple, stage: tuple, fill_value):
    if inits[0] != 0:
        logger.info(f"Filling offset of {inits[0]}s with {fill_value}")
        inits = (0,) + inits
        durs = (inits[1],) + durs
        stage = (fill_value,) + stage
    return inits, durs, stage


@hydra.main(config_path="./config", version_base="1.2")
def main(cfg: DictConfig):
    hydra_cfg = HydraConfig.get()
    logger.info(f"overrides:\n{OmegaConf.to_yaml(hydra_cfg.overrides)}")

    if cfg.hypno.prepare_func is not None:
        logger.info(f"Preparing hypnogram with {cfg.hypno.prepare_func}")
        instantiate(cfg.hypno.prepare_func, cfg=cfg, _recursive_=False)

    out_dir = os.path.abspath(os.path.join(cfg.general.save_dir, cfg.name))
    file_regex = os.path.join(cfg.general.base_dir, cfg.hypno.file_glob)
    id_regex = cfg.hypno.id_regex
    epoch_length = cfg.general.epoch_duration
    use_dir_names = cfg.use_dir_names
    write_offsets_to_file = cfg.hypno.write_offsets_to_file
    offsets = {}
    if cfg.hypno.extract_func is not None:
        extract_func = instantiate(cfg.hypno.extract_func, _partial_=True)
    else:
        extract_func = None

    files = glob(file_regex)
    n_files = len(files)
    logger.info(f"Found {n_files} files matching glob statement")
    if n_files == 0:
        return
    logger.info(f"Saving .ids files to '{out_dir}'")

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    for i, file_ in enumerate(files):
        if use_dir_names is False:
            name = os.path.splitext(os.path.split(file_)[-1])[0]
        elif use_dir_names is True:
            name = os.path.split(os.path.split(file_)[0])[-1]
        else:
            name = "_".join(file_.split(os.path.sep)[use_dir_names - 1 : -1])
        name = re.sub(id_regex, "\g<1>", name)
        out_dir_subject = os.path.join(out_dir, name)
        out_path = os.path.join(out_dir_subject, name + ".ids")
        logger.info(f"{i+1}/{n_files} Processing {name}")
        logger.info(f"-- In path    {file_}")
        logger.info(f"-- Out path   {out_path}")

        if not os.path.exists(out_dir_subject):
            os.mkdir(out_dir_subject)
        if os.path.exists(out_path):
            raise OSError(f"File already exists at '{out_path}'")

        inits, durs, stages = extract_ids_from_hyp_file(
            file_,
            period_length=epoch_length,
            sample_rate=cfg.general.sample_rate,
            extract_func=extract_func,
        )
        if write_offsets_to_file:
            offsets[name] = int(inits[0])
            inits = remove_offset(inits)
        else:
            inits, durs, stages = fill_offset(inits, durs, stages, "UNKNOWN")
        inits, durs, stages = fill_hyp_gaps(inits, durs, stages, "UNKNOWN")

        start_date = extract_start_time(file_)

        write_to_ids_file(
            inits, durs, stages, out_path, dict(cfg.general.rstages), start_date
        )

    if write_offsets_to_file:
        offsets_path = os.path.join(out_dir, "preparations", "offsets.json")
        os.makedirs(os.path.dirname(offsets_path), exist_ok=True)
        with open(offsets_path, "w") as f:
            json.dump(offsets, f)
        logger.info(f"Offsets written to {offsets_path}")


if __name__ == "__main__":
    main()
