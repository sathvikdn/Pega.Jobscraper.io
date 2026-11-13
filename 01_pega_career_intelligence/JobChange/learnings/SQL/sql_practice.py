import argparse
import math
from pathlib import Path
import sqlite3
import sys


EXPECTED = [
    [(101, 100), (102, 200), (103, 100)],
    [(6, 5, 3)],
    [(4, 'Dev')],
    [('paid', 7, 850), ('pending', 2, 380), ('refunded', 1, 150)],
    [(1, 350), (2, 300)],
    [(1, 3, 350), (2, 2, 300), (3, 1, 200), (4, 1, 0), (5, 0, 0), (6, 0, 0)],
    [(5,)],
    [(5,), (6,)],
    [(1,), (2,), (3,), (4,)],
    [(1, None), (2, 'Mira'), (3, 'Mira'), (4, 'Nikhil'), (5, 'Mira'), (6, 'Ravi'), (7, 'Ravi')],
    [(850,)],
    [(108, 200, 180)],
    [(850, 380, 150)],
    [(70,)],
    [(1, 106), (2, 109), (3, 108), (4, 107), (6, 110)],
    [('Engineering', 2, 120), ('Engineering', 3, 120), ('Sales', 6, 80), ('Sales', 7, 80)],
    [('Engineering', 1, 150), ('Engineering', 2, 120), ('Sales', 5, 100), ('Sales', 6, 80)],
    [(101, 1, 100), (102, 1, 300), (106, 1, 350), (103, 2, 100), (109, 2, 300), (108, 3, 200), (107, 4, 0)],
    [(101, 1, None), (102, 1, 100), (106, 1, -150), (103, 2, None), (109, 2, 100), (108, 3, None), (107, 4, None)],
    [(1, 350, 100 * 350 / 850), (2, 300, 100 * 300 / 850), (3, 200, 100 * 200 / 850), (4, 0, 0)],
    [(1,), (3,), (4,)],
    [(3, '2026-02-02 12:00:00', 'view', 2)],
    [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,)],
    [(1, 0), (2, 1), (3, 1), (4, 2), (5, 1), (6, 2), (7, 2)],
]


def matches(actual, expected):
    if len(actual) != len(expected):
        return False
    for actual_row, expected_row in zip(actual, expected):
        if len(actual_row) != len(expected_row):
            return False
        for actual_value, expected_value in zip(actual_row, expected_row):
            if isinstance(actual_value, (int, float)) and isinstance(expected_value, (int, float)):
                if not math.isclose(actual_value, expected_value, rel_tol=1e-9, abs_tol=1e-9):
                    return False
            elif actual_value != expected_value:
                return False
    return True


def verify(connection, folder):
    statements = [query.strip() for query in (folder / 'SQL_30_DAY_SOLUTIONS.sql').read_text(encoding='utf-8').split(';') if query.strip()]
    if len(statements) != len(EXPECTED):
        raise ValueError('Solution count does not match expected results.')
    for question, (statement, expected) in enumerate(zip(statements, EXPECTED), 1):
        actual = connection.execute(statement).fetchall()
        if not matches(actual, expected):
            raise AssertionError(f'Q{question:02d}: expected {expected!r}, got {actual!r}')
        print(f'Q{question:02d} PASS ({len(actual)} rows)')
    print('All 24 core solutions passed on SQLite ' + sqlite3.sqlite_version)
    print('This does not validate PostgreSQL-only syntax, query plans, or concurrency.')


def practice(connection):
    print('SQL practice: fresh in-memory lab. Nothing is saved to a database file.')
    print('Enter SQL ending with a semicolon. Commands: .quit, .tables, .schema, .expected N')
    print('This lab uses SQLite; PostgreSQL-only examples require PostgreSQL.')
    pending_lines = []
    while True:
        try:
            line = input('sql> ' if not pending_lines else '...> ')
            if not pending_lines and line.strip() == '.quit':
                return
            if not pending_lines and line.strip() == '.tables':
                print('customers, orders, order_items, employees, events')
                continue
            if not pending_lines and line.strip() == '.schema':
                for row in connection.execute("SELECT sql FROM sqlite_master WHERE type = 'table' ORDER BY name"):
                    print(row[0] + ';')
                continue
            if not pending_lines and line.strip().startswith('.expected '):
                question = int(line.strip().split()[1])
                if not 1 <= question <= len(EXPECTED):
                    raise ValueError('Choose a question from 1 to 24.')
                for row in EXPECTED[question - 1]:
                    print(row)
                continue
            pending_lines.append(line)
            statement = '\n'.join(pending_lines)
            if not sqlite3.complete_statement(statement):
                continue
            pending_lines.clear()
            cursor = connection.execute(statement)
            if cursor.description:
                print(' | '.join(column[0] for column in cursor.description))
                results = cursor.fetchall()
                for row in results:
                    print(' | '.join('NULL' if value is None else str(value) for value in row))
                print(f'{len(results)} rows')
            else:
                print(f'Statement executed; affected rows: {cursor.rowcount}. Restart for original data.')
        except (EOFError, KeyboardInterrupt):
            print('\nPractice ended.')
            return
        except (sqlite3.Error, ValueError, IndexError) as error:
            pending_lines.clear()
            print(f'Error: {error}')


def main():
    connection = None
    try:
        parser = argparse.ArgumentParser(description='Offline SQL learning lab using only Python standard library.')
        parser.add_argument('--check', action='store_true', help='Validate all 24 provided solutions against expected results.')
        arguments = parser.parse_args()
        folder = Path(__file__).resolve().parent
        connection = sqlite3.connect(':memory:', isolation_level=None)
        connection.execute('PRAGMA foreign_keys = ON')
        connection.executescript((folder / 'SQL_30_DAY_LAB.sql').read_text(encoding='utf-8'))
        if arguments.check:
            verify(connection, folder)
        else:
            practice(connection)
        return 0
    except (OSError, sqlite3.Error, ValueError, AssertionError) as error:
        print(f'Failed: {error}', file=sys.stderr)
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == '__main__':
    sys.exit(main())
