from __future__ import annotations

from functools import reduce
from operator import or_
from typing import Callable, TypeVar
from warnings import warn

from polars.internals import DataFrame, Expr, LazyFrame, Series

__all__ = [
    "register_expr_namespace",
    "register_dataframe_namespace",
    "register_lazyframe_namespace",
    "register_series_namespace",
]

# do not allow override of polars' own namespaces (as registered by '_accessors')
_reserved_namespaces: set[str] = reduce(
    or_,
    (
        cls._accessors  # type: ignore[attr-defined]
        for cls in (DataFrame, Expr, LazyFrame, Series)
    ),
)


NS = TypeVar("NS")


class NameSpace:
    """Establish property-like namespace object for user-defined functionality."""

    def __init__(self, name: str, namespace: type[NS]) -> None:
        self._accessor = name
        self._ns = namespace

    def __get__(self, instance: NS | None, cls: type[NS]) -> NS | type[NS]:
        if instance is None:
            return self._ns

        ns_instance = self._ns(instance)  # type: ignore[call-arg]
        setattr(instance, self._accessor, ns_instance)
        return ns_instance


def _create_namespace(
    name: str, cls: type[Expr | DataFrame | LazyFrame | Series]
) -> Callable[[type[NS]], type[NS]]:
    """Register custom namespace against the underlying polars class."""

    def namespace(ns_class: type[NS]) -> type[NS]:
        if name in _reserved_namespaces:
            raise AttributeError(f"Cannot override reserved namespace ({name!r})")
        elif hasattr(cls, name):
            warn(
                f"Overriding existing custom namespace {name!r} (on {cls.__name__})",
                UserWarning,
            )

        setattr(cls, name, NameSpace(name, ns_class))
        cls._accessors.add(name)
        return ns_class

    return namespace


def register_expr_namespace(name: str) -> Callable[[type[NS]], type[NS]]:
    """
    Decorator for registering custom functionality with a polars Expr namespace.

    Parameters
    ----------
    name
        Name under which the functionality will be accessed.

    Examples
    --------
    >>> @pl.api.register_expr_namespace("power")
    ... class PowersOfN:
    ...     def __init__(self, expr: pl.Expr):
    ...         self._expr = expr
    ...
    ...     def next(self, p: int) -> pl.Expr:
    ...         return (p ** (self._expr.log(p).ceil()).cast(pl.Int64)).cast(pl.Int64)
    ...
    ...     def previous(self, p: int) -> pl.Expr:
    ...         return (p ** (self._expr.log(p).floor()).cast(pl.Int64)).cast(pl.Int64)
    ...
    ...     def nearest(self, p: int) -> pl.Expr:
    ...         return (p ** (self._expr.log(p)).round(0).cast(pl.Int64)).cast(pl.Int64)
    >>>
    >>> df = pl.DataFrame([1.4, 24.3, 55.0, 64.001], columns=["n"])
    >>> df.select(
    ...     [
    ...         pl.col("n"),
    ...         pl.col("n").power.next(p=2).alias("next_pow2"),
    ...         pl.col("n").power.previous(p=2).alias("prev_pow2"),
    ...         pl.col("n").power.nearest(p=2).alias("nearest_pow2"),
    ...     ]
    ... )
    shape: (4, 4)
    ┌────────┬───────────┬───────────┬──────────────┐
    │ n      ┆ next_pow2 ┆ prev_pow2 ┆ nearest_pow2 │
    │ ---    ┆ ---       ┆ ---       ┆ ---          │
    │ f64    ┆ i64       ┆ i64       ┆ i64          │
    ╞════════╪═══════════╪═══════════╪══════════════╡
    │ 1.4    ┆ 2         ┆ 1         ┆ 1            │
    ├╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌╌╌╌╌╌┤
    │ 24.3   ┆ 32        ┆ 16        ┆ 32           │
    ├╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌╌╌╌╌╌┤
    │ 55.0   ┆ 64        ┆ 32        ┆ 64           │
    ├╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌╌╌╌╌╌┤
    │ 64.001 ┆ 128       ┆ 64        ┆ 64           │
    └────────┴───────────┴───────────┴──────────────┘

    See Also
    --------
    register_dataframe_namespace: Register functionality on a DataFrame.
    register_lazyframe_namespace: Register functionality on a LazyFrame.
    register_series_namespace: Register functionality on a Series.

    """
    return _create_namespace(name, Expr)


def register_dataframe_namespace(name: str) -> Callable[[type[NS]], type[NS]]:
    """
    Decorator for registering custom functionality with a polars DataFrame namespace.

    Parameters
    ----------
    name
        Name under which the functionality will be accessed.

    Examples
    --------
    >>> @pl.api.register_dataframe_namespace("split")
    ... class SplitFrame:
    ...     def __init__(self, df: pl.DataFrame):
    ...         self._df = df
    ...
    ...     def by_first_letter_of_column_names(self) -> list[pl.DataFrame]:
    ...         return [
    ...             self._df.select([col for col in self._df.columns if col[0] == f])
    ...             for f in dict.fromkeys(col[0] for col in self._df.columns)
    ...         ]
    ...
    ...     def by_first_letter_of_column_values(self, col: str) -> list[pl.DataFrame]:
    ...         return [
    ...             self._df.filter(pl.col(col).str.starts_with(c))
    ...             for c in sorted(
    ...                 set(df.select(pl.col(col).str.slice(0, 1)).to_series())
    ...             )
    ...         ]
    >>>
    >>> df = pl.DataFrame(
    ...     data=[["xx", 2, 3, 4], ["xy", 4, 5, 6], ["yy", 5, 6, 7], ["yz", 6, 7, 8]],
    ...     columns=["a1", "a2", "b1", "b2"],
    ...     orient="row",
    ... )
    >>> df
    shape: (4, 4)
    ┌─────┬─────┬─────┬─────┐
    │ a1  ┆ a2  ┆ b1  ┆ b2  │
    │ --- ┆ --- ┆ --- ┆ --- │
    │ str ┆ i64 ┆ i64 ┆ i64 │
    ╞═════╪═════╪═════╪═════╡
    │ xx  ┆ 2   ┆ 3   ┆ 4   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ xy  ┆ 4   ┆ 5   ┆ 6   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ yy  ┆ 5   ┆ 6   ┆ 7   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ yz  ┆ 6   ┆ 7   ┆ 8   │
    └─────┴─────┴─────┴─────┘
    >>> df.split.by_first_letter_of_column_names()
    [shape: (4, 2)
    ┌─────┬─────┐
    │ a1  ┆ a2  │
    │ --- ┆ --- │
    │ str ┆ i64 │
    ╞═════╪═════╡
    │ xx  ┆ 2   │
    ├╌╌╌╌╌┼╌╌╌╌╌┤
    │ xy  ┆ 4   │
    ├╌╌╌╌╌┼╌╌╌╌╌┤
    │ yy  ┆ 5   │
    ├╌╌╌╌╌┼╌╌╌╌╌┤
    │ yz  ┆ 6   │
    └─────┴─────┘,
    shape: (4, 2)
    ┌─────┬─────┐
    │ b1  ┆ b2  │
    │ --- ┆ --- │
    │ i64 ┆ i64 │
    ╞═════╪═════╡
    │ 3   ┆ 4   │
    ├╌╌╌╌╌┼╌╌╌╌╌┤
    │ 5   ┆ 6   │
    ├╌╌╌╌╌┼╌╌╌╌╌┤
    │ 6   ┆ 7   │
    ├╌╌╌╌╌┼╌╌╌╌╌┤
    │ 7   ┆ 8   │
    └─────┴─────┘]
    >>> df.split.by_first_letter_of_column_values("a1")
    [shape: (2, 4)
    ┌─────┬─────┬─────┬─────┐
    │ a1  ┆ a2  ┆ b1  ┆ b2  │
    │ --- ┆ --- ┆ --- ┆ --- │
    │ str ┆ i64 ┆ i64 ┆ i64 │
    ╞═════╪═════╪═════╪═════╡
    │ xx  ┆ 2   ┆ 3   ┆ 4   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ xy  ┆ 4   ┆ 5   ┆ 6   │
    └─────┴─────┴─────┴─────┘, shape: (2, 4)
    ┌─────┬─────┬─────┬─────┐
    │ a1  ┆ a2  ┆ b1  ┆ b2  │
    │ --- ┆ --- ┆ --- ┆ --- │
    │ str ┆ i64 ┆ i64 ┆ i64 │
    ╞═════╪═════╪═════╪═════╡
    │ yy  ┆ 5   ┆ 6   ┆ 7   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ yz  ┆ 6   ┆ 7   ┆ 8   │
    └─────┴─────┴─────┴─────┘]

    See Also
    --------
    register_expr_namespace: Register functionality on an Expr.
    register_lazyframe_namespace: Register functionality on a LazyFrame.
    register_series_namespace: Register functionality on a Series.

    """
    return _create_namespace(name, DataFrame)


def register_lazyframe_namespace(name: str) -> Callable[[type[NS]], type[NS]]:
    """
    Decorator for registering custom functionality with a polars LazyFrame namespace.

    Parameters
    ----------
    name
        Name under which the functionality will be accessed.

    Examples
    --------
    >>> @pl.api.register_lazyframe_namespace("split")
    ... class SplitFrame:
    ...     def __init__(self, ldf: pl.LazyFrame):
    ...         self._ldf = ldf
    ...
    ...     def by_column_dtypes(self) -> list[pl.LazyFrame]:
    ...         return [
    ...             self._ldf.select(pl.col(tp))
    ...             for tp in dict.fromkeys(self._ldf.dtypes)
    ...         ]
    >>>
    >>> ldf = pl.DataFrame(
    ...     data=[["xx", 2, 3, 4], ["xy", 4, 5, 6], ["yy", 5, 6, 7], ["yz", 6, 7, 8]],
    ...     columns=["a1", "a2", "b1", "b2"],
    ...     orient="row",
    ... ).lazy()
    >>>
    >>> ldf.collect()
    shape: (4, 4)
    ┌─────┬─────┬─────┬─────┐
    │ a1  ┆ a2  ┆ b1  ┆ b2  │
    │ --- ┆ --- ┆ --- ┆ --- │
    │ str ┆ i64 ┆ i64 ┆ i64 │
    ╞═════╪═════╪═════╪═════╡
    │ xx  ┆ 2   ┆ 3   ┆ 4   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ xy  ┆ 4   ┆ 5   ┆ 6   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ yy  ┆ 5   ┆ 6   ┆ 7   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ yz  ┆ 6   ┆ 7   ┆ 8   │
    └─────┴─────┴─────┴─────┘
    >>> [ldf.collect() for ldf in ldf.split.by_column_dtypes()]
    [shape: (4, 1)
    ┌─────┐
    │ a1  │
    │ --- │
    │ str │
    ╞═════╡
    │ xx  │
    ├╌╌╌╌╌┤
    │ xy  │
    ├╌╌╌╌╌┤
    │ yy  │
    ├╌╌╌╌╌┤
    │ yz  │
    └─────┘, shape: (4, 3)
    ┌─────┬─────┬─────┐
    │ a2  ┆ b1  ┆ b2  │
    │ --- ┆ --- ┆ --- │
    │ i64 ┆ i64 ┆ i64 │
    ╞═════╪═════╪═════╡
    │ 2   ┆ 3   ┆ 4   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ 4   ┆ 5   ┆ 6   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ 5   ┆ 6   ┆ 7   │
    ├╌╌╌╌╌┼╌╌╌╌╌┼╌╌╌╌╌┤
    │ 6   ┆ 7   ┆ 8   │
    └─────┴─────┴─────┘]

    See Also
    --------
    register_expr_namespace: Register functionality on an Expr.
    register_dataframe_namespace: Register functionality on a DataFrame.
    register_series_namespace: Register functionality on a Series.

    """
    return _create_namespace(name, LazyFrame)


def register_series_namespace(name: str) -> Callable[[type[NS]], type[NS]]:
    """
    Decorator for registering custom functionality with a polars Series namespace.

    Parameters
    ----------
    name
        Name under which the functionality will be accessed.

    Examples
    --------
    >>> @pl.api.register_series_namespace("math")
    ... class MathShortcuts:
    ...     def __init__(self, s: pl.Series):
    ...         self._s = s
    ...
    ...     def square(self) -> pl.Series:
    ...         return self._s * self._s
    ...
    ...     def cube(self) -> pl.Series:
    ...         return self._s * self._s * self._s
    >>>
    >>> s = pl.Series("n", [1.5, 31.0, 42.0, 64.5])
    >>> s.math.square().alias("s^2")
    shape: (4,)
    Series: 's^2' [f64]
    [
        2.25
        961.0
        1764.0
        4160.25
    ]
    >>> s = pl.Series("n", [1, 2, 3, 4, 5])
    >>> s.math.cube().alias("s^3")
    shape: (5,)
    Series: 's^3' [i64]
    [
        1
        8
        27
        64
        125
    ]

    See Also
    --------
    register_expr_namespace: Register functionality on an Expr.
    register_dataframe_namespace: Register functionality on a DataFrame.
    register_lazyframe_namespace: Register functionality on a LazyFrame.

    """
    return _create_namespace(name, Series)
