import sqlite3

from cleaver.experiment import Experiment


class SQLiteBackend(object):
    """
    Provides an interface for persisting and retrieving A/B test results
    to a SQLite database.

    Primarily a proof of concept/example implementation (not recommended for
    production usage).

    :param db a SQLite connection string, or a ``sqlite3.Connection`` object
    :param table_prefix an optional prefix for table names
    """

    def __init__(self, db, table_prefix='cleaver_'):
        if isinstance(basestring, db):
            self._conn = sqlite3.connect(db)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS e " \
                "(name TEXT PRIMARY KEY, started_on TEXT)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS v " \
                "(name TEXT PRIMARY KEY, experiment_name TEXT)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS i (" \
                "identity TEXT PRIMAY KEY," \
                "experiment_name TEXT," \
                "variant TEXT" \
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS p (" \
                "experiment_name TEXT," \
                "variant TEXT," \
                "total INTEGER DEFAULT 0," \
                "PRIMARY KEY (experiment_name, variant)" \
            ")"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS c (" \
                "experiment_name TEXT," \
                "variant TEXT," \
                "total INTEGER DEFAULT 0," \
                "PRIMARY KEY (experiment_name, variant)" \
            ")"
        )

    def close(self):
        self._conn.close()

    def _factory(self, row):
        return Experiment(
            backend=self,
            name=row['name'],
            started_on=row['started_on'],
            variants=[
                v['name']
                for v in self._conn.execute(
                    "SELECT * FROM v WHERE experiment_name = ?",
                    (row['name'],)
                )
            ]
        )

    def all_experiments(self):
        """
        Retrieve every available experiment.

        Returns a list of ``cleaver.experiment.Experiment``s
        """
        experiments = []
        for row in self._conn.execute("SELECT * FROM e"):
            experiments.append(self._factory(row))
        return experiments

    def get_experiment(self, name, variants):
        """
        Retrieve an experiment by its name and variants (assuming it exists).

        :param name a unique string name for the experiment
        :param variants a list of strings, each with a unique variant name

        Returns a ``cleaver.experiment.Experiment`` or ``None``
        """
        row = self._conn.execute(
            "SELECT * FROM e WHERE name=?",
            (name,)
        ).fetchone()
        return self._factory(row) if row else None

    def set_experiment(self, name, variants):
        """
        Persist an experiment and its variants (unless they already exist).

        :param name a unique string name for the experiment
        :param variants a list of strings, each with a unique variant name
        """
        self._conn.execute('INSERT INTO e (name) VALUES (?)', (name,))
        for v in variants:
            self._conn.execute(
                'INSERT INTO v (name, experiment_name) VALUES (?, ?)',
                (v, name)
            )

    def get_variant(self, identity, experiment_name):
        """
        Retrieve the variant for a specific user and experiment (if it exists).

        :param identity a unique user identifier
        :param experiment_name the string name of the experiment

        Returns a ``String`` or `None`
        """
        row = self._conn.execute(
            'SELECT * FROM i WHERE identity = ? AND experiment_name = ?',
            (identity, experiment_name)
        ).fetchone()
        return row['variant'] if row else None

    def participate(self, identity, experiment_name, variant):
        """
        Set the variant for a specific user and mark a participation for the
        experiment.

        :param identity a unique user identifier
        :param experiment_name the string name of the experiment
        :param variant the string name of the variant
        """
        self._conn.execute(
            'INSERT INTO i (identity, experiment_name, variant) ' \
                'VALUES (?, ?, ?)',
            (identity, experiment_name, variant)
        )
        self._conn.execute(
            'INSERT OR IGNORE INTO p (experiment_name, variant) VALUES (?, ?)',
            (experiment_name, variant)
        )
        self._conn.execute(
            'UPDATE p SET total = total + 1 WHERE ' \
                'experiment_name = ? AND variant = ?',
            (experiment_name, variant)
        )

    def score(self, experiment_name, variant):
        """
        Mark a conversion for a specific experiment variant.

        :param experiment_name the string name of the experiment
        :param variant the string name of the variant
        """
        self._conn.execute(
            'INSERT OR IGNORE INTO c (experiment_name, variant) VALUES (?, ?)',
            (experiment_name, variant)
        )
        self._conn.execute(
            'UPDATE c SET total = total + 1 WHERE ' \
                'experiment_name = ? AND variant = ?',
            (experiment_name, variant)
        )

    def participants(self, experiment_name, variant):
        """
        The number of participants for a certain variant.

        Returns an integer.
        """
        row = self._conn.execute(
            'SELECT total FROM p WHERE experiment_name = ? AND variant = ?',
            (experiment_name, variant)
        ).fetchone()
        return int(row['total']) if row and row['total'] else 0

    def conversions(self, experiment_name, variant):
        """
        The number of conversions for a certain variant.

        Returns an integer.
        """
        row = self._conn.execute(
            'SELECT total FROM c WHERE experiment_name = ? AND variant = ?',
            (experiment_name, variant)
        ).fetchone()
        return int(row['total']) if row and row['total'] else 0
