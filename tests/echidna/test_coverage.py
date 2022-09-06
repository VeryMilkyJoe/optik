import os
from typing import Optional, Tuple
from multiprocessing import Process
from time import sleep

import pytest
from optik.echidna import run_hybrid_echidna
from optik.echidna.interface import get_latest_coverage_file
from .common import new_test_dir, CONTRACTS_DIR

COVERAGE_TARGET_MARKER = "test::coverage"

# List of tests as tuples:
# (contract, coverage mode, tx sequence length)
to_test = [
    ("ExploreMe.sol", "inst", 40),
    ("Primality.sol", "inst", 40),
    ("MultiMagic.sol", "inst-tx-seq", 10),
    ("MultiMagic256.sol", "inst-tx-seq", 10),
    ("CoverageInt.sol", "inst", 40),
    ("CoverageBool.sol", "path-relaxed", 5),
    ("CoverageBytesM.sol", "path-relaxed", 1),
    ("CoverageBytes.sol", "path-relaxed", 2),
    ("CoverageString.sol", "path-relaxed", 2),
    # ("CoverageStaticTuple.sol", "inst-tx-seq", 5),
    # ("CoverageNestedTuple.sol", "inst-tx-seq", 5),
    # ("CoverageArrayOfTuple.sol", "inst-tx-seq", 1),
    # ("CoverageDynamicTuple1.sol", "inst-tx-seq", 1),
    # ("CoverageDynamicTuple3.sol", "inst-tx-seq", 1),
    # ("CoverageDynamicTuple2.sol", "inst-tx-seq", 1),
    ("CoverageNestedArrays1.sol", "inst-tx-seq", 1),
    ("CoverageNestedArrays2.sol", "inst-tx-seq", 1),
    ("CoverageNestedArrays3.sol", "inst-tx-seq", 1),
    ("CoverageFixedArray.sol", "inst-tx-seq", 10),
    ("CoverageDynamicArray.sol", "inst-tx-seq", 10),
    ("Time.sol", "inst", 10),
    ("SmartianExample.sol", "inst-tx-seq", 40),
    ("Payable.sol", "inst", 10),
    ("IntCast.sol", "inst-tx-seq", 5),
    ("CreateContracts.sol", "inst-tx-seq", 10),
    ("CreateContracts2.sol", "inst-tx-seq", 40),
    ("MessageCall.sol", "inst-tx-seq", 1),
    ("Reentrency.sol", "inst-tx-seq", 20),
]

to_test = [
    (CONTRACTS_DIR / contract_file, *rest) for contract_file, *rest in to_test
]

# Test coverage on every contract
@pytest.mark.parametrize("contract,cov_mode,seq_len", to_test)
def test_coverage(contract: str, cov_mode: str, seq_len: int):
    """Test coverage for a given contract. The function
    runs hybrid echidna on the contract and asserts that all target lines in the
    source code were reached. It does so by looking at the `covered.<timestamp>.txt`
    file generated by Echidna after fuzzing, and making that every line marked
    with the coverage test marker was reached (indicated by '*').
    """
    test_dir = new_test_dir()
    contract_name = contract.stem
    # Run hybrid echidna
    cmdline_args = f"{contract}  --contract {contract_name} --test-mode assertion --corpus-dir {test_dir} --seq-len {seq_len} --seed 46541521 --max-iters 10 --test-limit 10000 --cov-mode {cov_mode} --debug --logs stdout --no-display".split()
    # Run hybrid echidna in a separate process
    test_proc = Process(target=run_hybrid_echidna, args=(cmdline_args,))
    test_proc.start()
    # Detect early success in coverage test
    while test_proc.is_alive():
        covered_file = get_latest_coverage_file(test_dir)
        if check_coverage_success(covered_file)[0]:
            test_proc.terminate()
            break
        sleep(5)
    # Final coverage check
    success, err_msg = check_coverage_success(
        get_latest_coverage_file(test_dir)
    )
    assert success, err_msg


def check_coverage_success(covered_file: Optional[str]) -> Tuple[bool, str]:
    """Check if a coverage test contract was succesfully covered.
    Returns a tuple (success, error_msg)
    """

    if covered_file is None:
        return (
            False,
            "No coverage file available",
        )

    with open(covered_file, "r") as f:
        for i, line in enumerate(f.readlines()):
            if COVERAGE_TARGET_MARKER in line and not line[0] in ["*", "e"]:
                return (
                    False,
                    f"Failed to cover line {i+1}:\n|{''.join(line.split('|')[1:])}",
                )
        return (
            True,
            "",
        )
