# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""List all recognized versions of mathrace journal files."""

def list_journal_versions() -> list[str]:
    """
    List all recognized versions of mathrace journal files.

    Returns
    -------
    :
        A list of string representing all available versions.

        The version is the name of the revision in simdis, available from
        https://svn.dmf.unicatt.it/svn/projects/simdis

        Only versions after the 2013 edition are available. Earlier versions are not applicable because
        of backward incompatible regulation changes. All versions ignore lines starting with # and consider
        them as comments.

        The following versions are available:

        * r5539 (2013-01-18 01:21:11 +0100): initial version.

          This version uses the following race setup codes:
          ° --- 001: file begin
          ° --- 003: race definition
          ° --- 004: question definition
          ° --- 999: file end

          This version uses the following race event codes:
          ° 0 002: race start
          ° timestamp 010: jolly selection by a team
          ° timestamp 011: answer submission by a team
          ° timestamp 021: jolly timeout
          ° timestamp 022: timer update
          ° timestamp 027: race suspended
          ° timestamp 028: race resumed
          ° timestamp 029: race end
          ° timestamp 091: manual addition of a bonus

        * r11167 (2015-03-08 20:41:09 +0100): this version introduced some code changes in race events.

          All race event codes were changed as follows:
          ° 0 200: race start was changed from 002 to 200
          ° timestamp 101: timer update was changed from 022 to 101
          ° timestamp 110: answer submission by a team was changed from 011 to 110
          ° timestamp 120: jolly selection by a team was changed from 010 to 120
          ° timestamp 121: jolly timeout was changed from 021 to 121
          ° timestamp 130: manual addition of a bonus was changed from 091 to 130
          ° timestamp 201: race suspended was changed from 027 to 201
          ° timestamp 202: race resumed was changed from 028 to 202
          ° timestamp 210: race end was changed from 029 to 210

        * r11184 (2015-03-10 09:04:16 +0100): this version introduced protocol numbers in
          race events 110 and 120

        * r11189 (2015-03-10 12:01:10 +0100): this version added a further timer event.

          The following event setup codes were added:
          ° timestamp 901: timer update for the second timer.

        * r17497 (2019-05-29 00:55:27 +0200): this version added support for non-default k.

          The following race setup codes were changed:
          ° --- 003: race definition appends the value of k to the one of n with the notation n.k

        * r17505 (2019-05-30 21:37:33 +0200): this version added team definition as a race code.

          The following race setup codes were added:
          ° --- 005: team definition

        * r17548 (2019-06-07 21:45:05 +0200): this version added and alternative race definition.

          The following race setup codes were added:
          ° --- 002: alternative race definition

        * r20642 (2021-06-05 01:31:45 +0200): this version added bonus and superbonus race codes.

          The following race setup codes were added:
          ° --- 011: bonus definition
          ° --- 012: superbonus definition

        * r20644 (2021-06-08 01:36:41 +0200): this version prints human readable timestamps
          of the form hh:mm:ss.msec instead of number of elapsed seconds.

          This change affects all race event codes.

        * r25013 (2024-02-13 00:10:49 +0100): this version added an extra field to the question definition.
          The field currently stores a 0000 placeholder, but in future may store the exact answer to the question.

          The following race setup codes were changed:
          ° --- 004: question definition
    """
    return ["r5539", "r11167", "r11184", "r11189", "r17497", "r17505", "r17548", "r20642", "r20644", "r25013"]


if __name__ == "__main__":
    print(", ".join(list_journal_versions()))
