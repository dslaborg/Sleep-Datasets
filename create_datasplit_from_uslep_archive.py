import argparse
import os


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", "-p", required=True)
    return parser.parse_args()


def main():
    args = parse()
    dataset_folders = sorted(os.listdir(args.path))

    train_subjects = {}
    val_subjects = {}
    test_subjects = {}

    for folder in dataset_folders:
        for file in ["train.txt", "val.txt", "test.txt"]:
            if os.path.exists(os.path.join(args.path, folder, file)):
                with open(os.path.join(args.path, folder, file)) as f:
                    subjects = f.read().splitlines()

                if folder not in [
                    "dcsm",
                    "phys",
                    "sedf_st",
                    "sedf_sc",
                    "shhs",
                    "dod_o",
                    "dod_h",
                    "isruc_sg1",
                    "isruc_sg2",
                    "isruc_sg3",
                    "mass-c1",
                    "mass-c3",
                    "svuh",
                ]:
                    subjects = ["-".join(s.split("-")[1:]) for s in subjects]

                ds_name = folder

                if folder == "ccshs":
                    subjects = [s.replace("trec-", "") for s in subjects]
                if folder == "cfs":
                    subjects = [s.replace("visit5-", "") for s in subjects]
                if folder == "chat":
                    subjects = [
                        s.replace("baseline-nonrandomized", "nonrandomized")
                        for s in subjects
                    ]
                if folder == "dod_h":
                    ds_name = "dodh"
                if folder == "dod_o":
                    ds_name = "dodo"
                if folder == "hpap":
                    subjects = [
                        s.replace("lab-full-", "").replace("lab-split-", "")
                        for s in subjects
                    ]
                if folder == "mesa":
                    subjects = [s.replace("sleep-", "") for s in subjects]
                if folder == "phys":
                    subjects = [s.replace("tr", "") for s in subjects]
                if folder == "sedf_sc":
                    subjects = [s[3:6] for s in subjects]
                    ds_name = "sedf-sc"
                if folder == "sedf_st":
                    subjects = [s[3:6] for s in subjects]
                    ds_name = "sedf-st"
                if folder == "shhs":
                    subjects = [s[4:] for s in subjects]
                if folder == "sof":
                    subjects = [s.replace("visit-8-", "") for s in subjects]
                if (
                    folder == "isruc_sg1"
                    or folder == "isruc_sg2"
                    or folder == "isruc_sg3"
                ):
                    subjects = [
                        s.replace("subject_", "").replace("visit_", "")
                        for s in subjects
                    ]
                    ds_name = folder.replace("_", "-")
                if folder == "svuh":
                    subjects = [s.replace("ucddb", "") for s in subjects]

                if file == "train.txt":
                    train_subjects[ds_name] = subjects
                elif file == "val.txt":
                    val_subjects[ds_name] = subjects
                elif file == "test.txt":
                    test_subjects[ds_name] = subjects

    # write to yaml file
    with open("usleep_split.yaml", "w") as f:
        f.write("train:\n")
        for key, value in train_subjects.items():
            f.write(f"  {key}:\n")
            for item in value:
                f.write(f'    - "{item}"\n')

        f.write("valid:\n")
        for key, value in val_subjects.items():
            f.write(f"  {key}:\n")
            for item in value:
                f.write(f'    - "{item}"\n')

        f.write("test:\n")
        for key, value in test_subjects.items():
            f.write(f"  {key}:\n")
            for item in value:
                f.write(f'    - "{item}"\n')


if __name__ == "__main__":
    main()
