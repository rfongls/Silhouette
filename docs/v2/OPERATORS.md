# Engine Contracts

## Messages and Results

```python
@dataclass(slots=True)
class Message:
    id: str
    raw: bytes
    meta: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class Issue:
    severity: Literal["error", "warning", "passed"]
    code: str
    segment: str | None = None
    field: str | int | None = None
    component: str | int | None = None
    subcomponent: str | int | None = None
    value: str | None = None
    message: str | None = None

@dataclass(slots=True)
class Result:
    message: Message
    issues: list[Issue] = field(default_factory=list)
```

## Abstract Base Classes

```python
class Adapter(ABC):
    name: str

    @abstractmethod
    async def stream(self) -> AsyncIterator[Message]:
        ...

class Operator(ABC):
    name: str

    @abstractmethod
    async def process(self, msg: Message) -> Result:
        ...

class Sink(ABC):
    name: str

    @abstractmethod
    async def write(self, result: Result) -> None:
        ...
```

Adapters stream `Message` objects into the pipeline, operators return a new `Result` per message, and sinks persist or forward those results. Operators should preserve the inbound `Message` (with optional modifications) and append issues to capture validation or enrichment outcomes.
