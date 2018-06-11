import pandas as pd


def _count_header_rows(fn):
    header_rows = 0
    with open(fn) as f:
        for row in f.readlines():
            if row.startswith('#'):
                header_rows += 1
            else:
                break
    return header_rows


def load_cfp_files_into_dataframe(precinct_fn, election_results_fn, district_plan_fn):
    # TODO: Are we going to keep the same CSV/TSV file input?  Should we define some other standard?
    #     Going with existing files for now.
    df = pd.read_csv(precinct_fn, skiprows=2, sep='\t')

    df = df.set_index(' ')
    df.index.name = 'Subunit ID'
    expected_precinct_columns = ('nb', 'sp', 'area', 'pop')
    if not all(col in df.columns for col in expected_precinct_columns):
        raise ValueError("Didn't get expected minimum columns from precinct file.  "
                         "Expected columns are {}".format(expected_precinct_columns))

    election_results = pd.read_csv(election_results_fn,
                                   skiprows=_count_header_rows(election_results_fn), header=None)
    if len(election_results) != len(df):
        raise ValueError("Election results has a different number of records than "
                         "precinct file (%d vs %d)" % (len(election_results), len(df)))

    df['voteA'] = election_results[1]
    df['voteB'] = election_results[2]

    district_plan = pd.read_csv(district_plan_fn, skiprows=_count_header_rows(district_plan_fn),
                                header=None)
    if len(district_plan) != len(df):
        raise ValueError("District plan has a different number of records than precinct file"
                         "(%d vs %d)" % (len(district_plan), len(df)))
    df['district'] = district_plan[1]

    return df
