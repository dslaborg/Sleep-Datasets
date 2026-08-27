import logging
import os
from os.path import join

import numpy as np
import pyedflib
from psg_utils.downloads import preprocess_phys_hypnograms

from utils.dreem_consensus_builder import ConsensusBuilder

logger = logging.getLogger(__name__)

lights_off_events = {
    "dodh": {
        "5bf0f969-304c-581e-949c-50c108f62846": 60,  # renamed from 63b799f6-8a4f-4224-8797-ea971f78fb53
        "b5d5785d-87ee-5078-b9b9-aac6abd4d8de": 60,  # renamed from de3af7b1-ab6f-43fd-96f0-6fc64e8d2ed4
    },
    "dodo": {},
}
lights_on_events = {
    "dodh": {
        "3e842aa8-bcd9-521e-93a2-72124233fe2c": 620,  # renamed from a14f8058-f636-4be7-a67a-8f7f91a419e7
    },
    "dodo": {},
}


def prepare_gs_dreem(dataset, file_dir, out_dir, cfg):
    file_dir = join(cfg.general.base_dir, file_dir)
    out_dir = join(cfg.general.base_dir, out_dir)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    consensus_builder = ConsensusBuilder(
        file_dir,
        lights_on=lights_on_events[dataset],
        lights_off=lights_off_events[dataset],
    )
    consensus_all_scorers = consensus_builder.result_hypnograms_consensus
    consensus_n_minus_one_scorers = (
        consensus_builder.result_hypnograms_consensus_n_minus_one
    )

    stage_dict = {-1: "UNKNOWN", 0: "W", 1: "N1", 2: "N2", 3: "N3", 4: "REM"}

    for s_id in consensus_all_scorers:
        gs_hypnogram_n_minus_one = consensus_n_minus_one_scorers[s_id][0]
        gs_hypnogram_n_minus_one = np.array(
            [stage_dict[s] for s in gs_hypnogram_n_minus_one]
        )

        out_path = join(out_dir, s_id + ".npy")
        if os.path.exists(out_path):
            logger.info(f"File {out_path} already exists, skipping")
            continue
        np.save(out_path, gs_hypnogram_n_minus_one)


def prepare_phys(dataset_folder_path: str, out_dir: str, cfg):
    path = join(cfg.general.base_dir, dataset_folder_path)
    preprocess_phys_hypnograms(path, out_dir)


def extract_from_txt(
    file_path: str, stage_dict, period_length, **kwargs: dict
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    stages = np.genfromtxt(file_path, dtype=str)
    stages = np.array([stage_dict[s] for s in stages])
    durs = np.empty_like(stages, dtype=int)
    durs.fill(period_length)
    init = np.append([0], np.cumsum(durs))

    return init, durs, stages


def extract_from_edf(
    file_path: str, **kwargs: dict
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    edf_hypno = pyedflib.EdfReader(file_path)
    annot = edf_hypno.read_annotation()

    init = np.array([each_list[0] / 10_000_000 for each_list in annot], dtype=int)
    durs = np.array([each_list[1] for each_list in annot], dtype=int)
    stages = np.array([each_list[2] for each_list in annot], dtype=str)

    return init, durs, stages
