from typing import Any, Never
from ..client import DockerClient

class Model:
    """
    A base class for representing a single object on the server.
    """
    id_attribute = 'Id'

    def __init__(self, attrs=None, client: DockerClient | None = None, collection: "Collection" | None = None) -> None:
        assert client is not None
        #: A client pointing at the server that this object is on.
        self.client = client

        #: The collection that this model is part of.
        self.collection = collection

        #: The raw representation of this object from the API
        self.attrs = attrs
        if self.attrs is None:
            self.attrs = {}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.short_id}>"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.id == other.id

    def __hash__(self) -> int:
        return hash(f"{self.__class__.__name__}:{self.id}")

    @property
    def id(self) -> str:
        """
        The ID of the object.
        """
        return self.attrs.get(self.id_attribute)

    @property
    def short_id(self) -> str:
        """
        The ID of the object, truncated to 12 characters.
        """
        return self.id[:12]

    def reload(self) -> None:
        """
        Load this object from the server again and update ``attrs`` with the
        new data.
        """
        new_model = self.collection.get(self.id)
        self.attrs = new_model.attrs


class Collection:
    """
    A base class for representing all objects of a particular type on the
    server.
    """

    #: The type of object this collection represents, set by subclasses
    model: type[Model]

    # TODO This used to have = None
    def __init__(self, client: DockerClient) -> None:
        #: The client pointing at the server that this collection of objects
        #: is on.
        self.client = client

    def __call__(self, *args, **kwargs: Any) -> Never:
        raise TypeError(
            f"'{self.__class__.__name__}' object is not callable. "
            "You might be trying to use the old (pre-2.0) API - "
            "use docker.APIClient if so."
        )

    def list(self) -> list[Any]:
        raise NotImplementedError

    def get(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def create(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def prepare_model(self, attrs) -> Any:
        """
        Create a model from a set of attributes.
        """
        if isinstance(attrs, Model):
            attrs.client = self.client
            attrs.collection = self
            return attrs
        elif isinstance(attrs, dict):
            return self.model(attrs=attrs, client=self.client, collection=self)
        else:
            raise Exception(f"Can't create {self.model.__name__} from {attrs}")
