import os

import pytest

from rundmcmc import models

thisdir = os.path.dirname(__file__)
data_dir = os.path.join(thisdir, 'data')


def test_load_files_into_dataframe():
    precint_file = os.path.join(data_dir, 'precincts.txt')
    election_file = os.path.join(data_dir, 'elections', 'sen10.csv')
    plan_file = os.path.join(data_dir, 'plans', '2011.csv')
    df = models.load_files_into_dataframe(precint_file, election_file, plan_file)
    assert len(df) == 9059


def test_precincts_file_missing_column():
    precint_file = os.path.join(data_dir, 'precincts_missing_nb.txt')
    election_file = os.path.join(data_dir, 'elections', 'sen10.csv')
    plan_file = os.path.join(data_dir, 'plans', '2011.csv')
    with pytest.raises(ValueError):
        models.load_files_into_dataframe(precint_file, election_file, plan_file)


def test_load_election_file_with_wrong_rows():
    precint_file = os.path.join(data_dir, 'precincts.txt')
    election_file = os.path.join(data_dir, 'elections', 'sen10_missing_row.csv')
    plan_file = os.path.join(data_dir, 'plans', '2011.csv')

    with pytest.raises(ValueError):
        models.load_files_into_dataframe(precint_file, election_file, plan_file)


def test_load_election_file_with_header():
    precint_file = os.path.join(data_dir, 'precincts.txt')
    election_file = os.path.join(data_dir, 'elections', 'sen10_header.csv')
    plan_file = os.path.join(data_dir, 'plans', '2011.csv')
    df = models.load_files_into_dataframe(precint_file, election_file, plan_file)
    assert len(df) == 9059


def test_load_precint_file_with_wrong_rows():
    precint_file = os.path.join(data_dir, 'precincts.txt')
    election_file = os.path.join(data_dir, 'elections', 'sen10.csv')
    plan_file = os.path.join(data_dir, 'plans', '2011_missing_row.csv')

    with pytest.raises(ValueError):
        models.load_files_into_dataframe(precint_file, election_file, plan_file)


def test_load_precint_file_with_header():
    precint_file = os.path.join(data_dir, 'precincts.txt')
    election_file = os.path.join(data_dir, 'elections', 'sen10.csv')
    plan_file = os.path.join(data_dir, 'plans', '2011_header.csv')
    df = models.load_files_into_dataframe(precint_file, election_file, plan_file)
    assert len(df) == 9059
