"""Unit tests for the shared driver CLI helpers (corrosim.runs._cli, issue #64).

These pin the boilerplate the drivers now single-source: molecule parsing, the
shared --molecules default, JSON round-trips (which close their handles), table
printing and the +H+ suffix strip.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd
import pytest

from corrosim.presets import ARGHEL
from corrosim.runs import _cli


def test_parse_molecules_strips_and_drops_blanks():
    assert _cli.parse_molecules(" quercetin , kaempferol ,, ") == ["quercetin", "kaempferol"]
    assert _cli.parse_molecules("") == []


def test_resolve_case_fills_unset_molecules_from_the_case():
    p = argparse.ArgumentParser()
    _cli.add_case_arg(p)
    _cli.add_molecules_arg(p)
    args = p.parse_args([])
    _cli.resolve_case(args)
    assert _cli.parse_molecules(args.molecules) == list(ARGHEL.molecules)
    # and an explicit override still flows through
    over = p.parse_args(["--molecules", "caffeine,phenol"])
    _cli.resolve_case(over)
    assert _cli.parse_molecules(over.molecules) == ["caffeine", "phenol"]


def test_resolve_case_fills_metal_label_or_element():
    def parse(metal_mode, argv):
        p = argparse.ArgumentParser()
        _cli.add_case_arg(p)
        p.add_argument("--metal", default=None)
        args = p.parse_args(argv)
        _cli.resolve_case(args, metal=metal_mode)
        return args.metal

    # label mode keeps the facet (Fe(110)); element mode strips it (Fe)
    assert parse("label", []) == ARGHEL.metal
    assert parse("element", []) == ARGHEL.metal_element
    # an explicit --metal always wins over the case default
    assert parse("element", ["--metal", "Cu"]) == "Cu"


def test_resolve_case_selects_by_name_and_rejects_unknown():
    p = argparse.ArgumentParser()
    _cli.add_case_arg(p)
    _cli.add_molecules_arg(p)
    # the "argel" alias resolves to the same shipped study
    args = p.parse_args(["--case", "argel"])
    assert _cli.resolve_case(args) is ARGHEL
    assert _cli.parse_molecules(args.molecules) == list(ARGHEL.molecules)
    # an unknown case name is a hard error, not a silent default
    bad = p.parse_args(["--case", "nope"])
    with pytest.raises(KeyError):
        _cli.resolve_case(bad)


def test_write_json_then_read_json_roundtrip(tmp_path):
    path = str(tmp_path / "rows.json")
    obj = [{"name": "quercetin", "e_ads_kjmol": -7.45}]
    _cli.write_json(path, obj)
    assert json.loads((tmp_path / "rows.json").read_text()) == obj  # is valid, closed JSON
    assert _cli.read_json(path) == obj


def test_read_json_missing_returns_default_or_raises(tmp_path):
    missing = str(tmp_path / "nope.json")
    assert _cli.read_json(missing, []) == []            # explicit default
    assert _cli.read_json(missing, default=None) is None
    with pytest.raises(FileNotFoundError):              # no default -> propagates
        _cli.read_json(missing)


def test_print_table_accepts_rows_and_dataframe(capsys):
    rows = [{"name": "a", "val": 1.23456}, {"name": "b", "val": 2.0}]
    _cli.print_table(rows, columns=["name", "val"], round_to=2)
    out = capsys.readouterr().out
    assert "name" in out and "1.23" in out and "2.0" in out
    assert "index" not in out                            # index is suppressed

    _cli.print_table(pd.DataFrame(rows))                 # DataFrame path
    assert "1.23456" in capsys.readouterr().out          # unrounded when round_to is None


def test_strip_protonation_suffix_only_trims_trailing_tag():
    s = pd.Series(["quercetin+H+", "kaempferol", "iso+H+rhamnetin"])
    out = _cli.strip_protonation_suffix(s)
    assert list(out) == ["quercetin", "kaempferol", "iso+H+rhamnetin"]
