# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mock turing models to be used when turing itself is not available."""

import abc
import datetime
import typing

from mathrace_interaction.typing import TuringDict


class SquadraObjects:
    """A mock list of objects returned by Squadra.objects."""

    def get(self, gara: "Gara", num: int) -> "Squadra":
        """Get the pk-th element."""
        return gara.squadre[num - 1]

class Squadra:
    """A mock turing Squadra class."""

    objects = SquadraObjects()  # :SquadraObjects: list of all objects of type Squadra

    def __init__(self, **kwargs: typing.Any) -> None:  # noqa: ANN401
        self.gara: Gara | None = None
        self.nome: str | None = None
        self.num: int | None = None
        self.ospite: bool | None = None
        for key in ("gara", "nome", "num", "ospite"):
            if key in kwargs:
                setattr(self, key, kwargs[key])

    def save(self) -> None:
        """Save the current object into the corresponding list of self.gara, if not present already."""
        assert self.gara is not None
        if self not in self.gara.squadre:
            self.gara.squadre.append(self)

    def to_dict(self) -> TuringDict:
        """Convert to a dictionary."""
        for key in ("nome", "num", "ospite"):
            assert getattr(self, key) is not None, f"{key} is still set to None"
        return {
            "nome": self.nome,
            "num": self.num,
            "ospite": self.ospite
        }


class Soluzione:
    """A mock turing Soluzione class."""

    def __init__(self, **kwargs: typing.Any) -> None:  # noqa: ANN401
        self.gara: Gara | None = None
        self.problema: int | None = None
        self.nome: str | None = None
        self.risposta: int | None = None
        self.punteggio: int | None = None
        for key in ("gara", "problema", "nome", "risposta", "punteggio"):
            if key in kwargs:
                setattr(self, key, kwargs[key])

    def save(self) -> None:
        """Save the current object into the corresponding list of self.gara, if not present already."""
        assert self.gara is not None
        if self not in self.gara.soluzioni:
            self.gara.soluzioni.append(self)

    def to_dict(self) -> TuringDict:
        """Convert to a dictionary."""
        for key in ("problema", "nome", "risposta", "punteggio"):
            assert getattr(self, key) is not None, f"{key} is still set to None"
        return {
            "problema": self.problema,
            "nome": self.nome,
            "risposta": self.risposta,
            "punteggio": self.punteggio
        }


class Evento(abc.ABC):
    """A mock turing Evento class."""

    def __init__(self, **kwargs: typing.Any) -> None:  # noqa: ANN401
        self.gara: Gara | None = None
        self.orario: datetime.datetime | None = None
        self.squadra: Squadra | None = None
        for key in ("gara", "squadra"):
            if key in kwargs:
                setattr(self, key, kwargs[key])
        assert "squadra_id" not in kwargs
        if "squadra" in kwargs:
            squadra = kwargs["squadra"]
            assert isinstance(squadra, Squadra)
            self.squadra = squadra
        if "orario" in kwargs:
            orario = kwargs["orario"]
            if isinstance(orario, str):
                self.orario = datetime.datetime.fromisoformat(orario)
            elif isinstance(orario, datetime.datetime):
                self.orario = orario
            else:  # pragma: no cover
                raise RuntimeError("Invalid datetime value")

    def save(self) -> None:
        """Save the current object into the corresponding list of self.gara, if not present already."""
        assert self.gara is not None
        if self not in self.gara.eventi:
            self.gara.eventi.append(self)

    @abc.abstractmethod
    def to_dict(self) -> TuringDict:
        """Convert to a dictionary."""
        pass  # pragma: no cover


class Consegna(Evento):
    """A mock turing Consegna class."""

    def __init__(self, **kwargs: typing.Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
        self.problema: int | None = None
        self.risposta: int | None = None
        for key in ("problema", "risposta"):
            if key in kwargs:
                setattr(self, key, kwargs[key])

    def to_dict(self) -> TuringDict:
        """Convert to a dictionary."""
        for key in ("orario", "squadra", "problema", "risposta"):
            assert getattr(self, key) is not None, f"{key} is still set to None"
        return {
            "subclass": "Consegna",
            "orario": self.orario.isoformat(),  # type: ignore[union-attr]
            "problema": self.problema,
            "risposta": self.risposta,
            "squadra_id": self.squadra.num  # type: ignore[union-attr]
        }


class Jolly(Evento):
    """A mock turing Jolly class."""

    def __init__(self, **kwargs: typing.Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
        self.problema: int | None = None
        if "problema" in kwargs:
            setattr(self, "problema", kwargs["problema"])

    def to_dict(self) -> TuringDict:
        """Convert to a dictionary."""
        for key in ("orario", "squadra", "problema"):
            assert getattr(self, key) is not None, f"{key} is still set to None"
        return {
            "subclass": "Jolly",
            "orario": self.orario.isoformat(),  # type: ignore[union-attr]
            "problema": self.problema,
            "squadra_id": self.squadra.num  # type: ignore[union-attr]
        }


class Bonus(Evento):
    """A mock turing Bonus class."""

    def __init__(self, **kwargs: typing.Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
        self.punteggio: int | None = None
        if "punteggio" in kwargs:
            setattr(self, "punteggio", kwargs["punteggio"])

    def to_dict(self) -> TuringDict:
        """Convert to a dictionary."""
        for key in ("orario", "squadra", "punteggio"):
            assert getattr(self, key) is not None, f"{key} is still set to None"
        return {
            "subclass": "Bonus",
            "orario": self.orario.isoformat(),  # type: ignore[union-attr]
            "punteggio": self.punteggio,
            "squadra_id": self.squadra.num  # type: ignore[union-attr]
        }


class GaraObjects(list["Gara"]):
    """A mock list of objects returned by Gara.objects."""

    def get(self, pk: int) -> "Gara":
        """Get the pk-th element."""
        return self[pk]


class Gara:
    """A mock turing Gara class."""

    objects = GaraObjects()  # :GaraObjects: list of all objects of type Gara

    def __init__(self) -> None:
        self._pk: int | None = None
        self.nome: str | None = None
        self.inizio: datetime.datetime | None = None
        self.durata: datetime.timedelta | None = None
        self.n_blocco: int | None = None
        self.k_blocco: int | None = None
        self.durata_blocco: datetime.timedelta | None = None
        self.num_problemi: int | None = None
        self.punteggio_iniziale_squadre: int | None = None
        self.fixed_bonus: str | None = None
        self.super_mega_bonus: str | None = None
        self.jolly: bool | None = None
        self.eventi: list[Evento] = []
        self.soluzioni: list[Soluzione] = []
        self.squadre: list[Squadra] = []

    @property
    def pk(self) -> int:
        """Index of this object in the objects list."""
        assert self._pk is not None
        return self._pk

    def to_dict(self) -> TuringDict:
        """Convert to a dictionary."""
        for key in (
            "nome", "inizio", "durata", "durata_blocco", "num_problemi", "fixed_bonus", "super_mega_bonus", "jolly"
            # "n_blocco", "k_blocco", "punteggio_iniziale_squadre" are optional
        ):
            assert getattr(self, key) is not None, f"{key} is still set to None"
        return {
            "nome": self.nome,
            "inizio": self.inizio.isoformat(),  # type: ignore[union-attr]
            "durata": self.durata.seconds // 60,  # type: ignore[union-attr]
            "n_blocco": self.n_blocco,
            "k_blocco": self.k_blocco,
            "durata_blocco": self.durata_blocco.seconds // 60,  # type: ignore[union-attr]
            "num_problemi": self.num_problemi,
            "punteggio_iniziale_squadre": self.punteggio_iniziale_squadre,
            "fixed_bonus": self.fixed_bonus,
            "jolly": self.jolly,
            "super_mega_bonus": self.super_mega_bonus,
            "eventi": [e.to_dict() for e in self.eventi],
            "soluzioni": [s.to_dict() for s in self.soluzioni],
            "squadre": [s.to_dict() for s in self.squadre]
        }

    def save(self) -> None:
        """Save the current object into the list of objects, if not present already."""
        if self._pk is None:
            self._pk = len(self.objects)
            self.objects.append(self)
        else:
            assert self in self.objects

    @classmethod
    def create_from_dict(cls, data: TuringDict) -> typing.Self:
        """Create a Gara object from a dictionary, and save it into the list of Gara objects."""
        assert data["num_problemi"] == len(data["soluzioni"])

        this = cls()

        for k in (
            "nome", "n_blocco", "k_blocco", "num_problemi", "punteggio_iniziale_squadre", "fixed_bonus",
            "super_mega_bonus", "jolly"
        ):
            setattr(this, k, data[k])

        inizio = data["inizio"]
        if isinstance(inizio, str):
            this.inizio = datetime.datetime.fromisoformat(inizio)
        elif isinstance(inizio, datetime.datetime):  # pragma: no cover
            this.inizio = inizio
        elif inizio is None:
            this.inizio = None
        else:  # pragma: no cover
            raise RuntimeError("Invalid datetime value")
        this.durata = datetime.timedelta(minutes=data["durata"])
        this.durata_blocco = datetime.timedelta(minutes=data["durata_blocco"])

        for sq_data in data["squadre"]:
            sq_obj = Squadra(gara=this, **sq_data)
            assert sq_obj.num == len(this.squadre) + 1
            sq_obj.save()

        for so_data in data["soluzioni"]:
            so_obj = Soluzione(gara=this, **so_data)
            assert so_obj.problema == len(this.soluzioni) + 1
            so_obj.save()

        for e_data in data["eventi"]:
            e_class: type[Evento]
            if e_data["subclass"] == "Consegna":
                e_class = Consegna
            elif e_data["subclass"] == "Jolly":
                e_class = Jolly
            elif e_data["subclass"] == "Bonus":
                e_class = Bonus
            else:  # pragma: no cover
                raise RuntimeError("Invalid event")

            e_data_copy = dict(e_data)
            e_data_copy["squadra"] = Squadra.objects.get(gara=this, num=e_data["squadra_id"])
            del e_data_copy["squadra_id"]

            e_obj = e_class(gara=this, **e_data_copy)
            e_obj.save()

        this.save()
        return this
