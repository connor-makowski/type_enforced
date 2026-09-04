from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Any, Type
import pytest
import type_enforced


# ---------------------------------------------------------------------------
# 1. Multiple Inheritance & Diamond Inheritance
# ---------------------------------------------------------------------------
class BaseComponent:
    def __init__(self, name: str = "base"):
        self.name = name


class LeftFeature(BaseComponent):
    def left_action(self) -> str:
        return f"{self.name}:left"


class RightFeature(BaseComponent):
    def right_action(self) -> str:
        return f"{self.name}:right"


class CompositeWidget(LeftFeature, RightFeature):
    def combined_action(self) -> str:
        return f"{self.left_action()}+{self.right_action()}"


class UnrelatedWidget:
    def __init__(self, name: str = "unrelated"):
        self.name = name


@type_enforced.Enforcer
class ComponentService:
    def process_base(self, comp: BaseComponent) -> str:
        return comp.name

    def process_left(self, comp: LeftFeature) -> str:
        return comp.left_action()

    def process_right(self, comp: RightFeature) -> str:
        return comp.right_action()

    def process_composite(self, comp: CompositeWidget) -> str:
        return comp.combined_action()


def test_multiple_and_diamond_inheritance():
    service = ComponentService()
    widget = CompositeWidget("widget1")
    left = LeftFeature("left1")
    right = RightFeature("right1")
    base = BaseComponent("base1")
    unrelated = UnrelatedWidget("unrelated1")

    # CompositeWidget satisfies BaseComponent, LeftFeature, RightFeature, CompositeWidget
    assert service.process_base(widget) == "widget1"
    assert service.process_left(widget) == "widget1:left"
    assert service.process_right(widget) == "widget1:right"
    assert service.process_composite(widget) == "widget1:left+widget1:right"

    # LeftFeature satisfies BaseComponent & LeftFeature, but not RightFeature or CompositeWidget
    assert service.process_base(left) == "left1"
    assert service.process_left(left) == "left1:left"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `comp`"
    ):
        service.process_right(left)
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `comp`"
    ):
        service.process_composite(left)

    # RightFeature satisfies BaseComponent & RightFeature, but not LeftFeature or CompositeWidget
    assert service.process_base(right) == "right1"
    assert service.process_right(right) == "right1:right"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `comp`"
    ):
        service.process_left(right)
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `comp`"
    ):
        service.process_composite(right)

    # BaseComponent only satisfies BaseComponent
    assert service.process_base(base) == "base1"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `comp`"
    ):
        service.process_left(base)

    # Unrelated class fails all
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `comp`"
    ):
        service.process_base(unrelated)


# ---------------------------------------------------------------------------
# 2. Abstract Base Classes (ABC) & Runtime Checkable Protocols
# ---------------------------------------------------------------------------
class DataSource(ABC):
    @abstractmethod
    def fetch_records(self, query: str) -> list[str]:
        pass


class SqlSource(DataSource):
    def fetch_records(self, query: str) -> list[str]:
        return [f"sql:{query}"]


class RestSource(DataSource):
    def fetch_records(self, query: str) -> list[str]:
        return [f"rest:{query}"]


@runtime_checkable
class Serializable(Protocol):
    def serialize(self) -> str: ...


class JsonPayload:
    def serialize(self) -> str:
        return '{"key": "value"}'


class NonSerializablePayload:
    pass


@type_enforced.Enforcer
class PipelineManager:
    def __init__(self, source: DataSource):
        self.source = source

    def run_query(self, query: str) -> list[str]:
        return self.source.fetch_records(query)

    def export(self, payload: Serializable) -> str:
        return payload.serialize()


def test_abc_and_protocols():
    # ABC concrete implementations pass
    pipeline_sql = PipelineManager(SqlSource())
    assert pipeline_sql.run_query("SELECT 1") == ["sql:SELECT 1"]

    pipeline_rest = PipelineManager(RestSource())
    assert pipeline_rest.run_query("/api/v1") == ["rest:/api/v1"]

    # Non-DataSource passes fail
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `source`"
    ):
        PipelineManager("not_a_source")

    # Runtime checkable protocol passes with matching interface
    assert pipeline_sql.export(JsonPayload()) == '{"key": "value"}'

    # Protocol check fails with non-matching interface
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `payload`"
    ):
        pipeline_sql.export(NonSerializablePayload())


# ---------------------------------------------------------------------------
# 3. Dataclasses: frozen, kw_only, and field defaults
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
@dataclass(frozen=True)
class FrozenEndpoint:
    url: str
    port: int
    active: bool = True


@type_enforced.Enforcer
@dataclass(kw_only=True)
class ServerConfig:
    host: str
    port: int = 8080
    workers: int = 4


def test_dataclasses_frozen_and_kwonly():
    # Frozen dataclass validation
    ep = FrozenEndpoint("https://example.com", 443)
    assert ep.url == "https://example.com"
    assert ep.port == 443
    assert ep.active is True

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `port`"
    ):
        FrozenEndpoint("https://example.com", "443")

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `url`"
    ):
        FrozenEndpoint(123, 443)

    # Kw-only dataclass validation
    cfg = ServerConfig(host="127.0.0.1", port=9000)
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 9000
    assert cfg.workers == 4

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `host`"
    ):
        ServerConfig(host=127)

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `port`"
    ):
        ServerConfig(host="localhost", port="invalid_port")


# ---------------------------------------------------------------------------
# 4. Class Methods, Static Methods & Varied Receiver Names
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
class MultiReceiverService:
    prefix: str = "GLOBAL"

    @classmethod
    def create_prefixed(cls, text: str) -> str:
        return f"{cls.prefix}:{text}"

    @staticmethod
    def calculate_hash(val: int) -> int:
        return val ^ 0x55AA

    def method_this(this, a: int, b: str) -> str:
        return f"this:{a}:{b}"

    def method_me(me, items: list[int]) -> int:
        return sum(items)

    def method_ctx(ctx, key: str, value: float) -> str:
        return f"{key}={value}"

    def method_custom(custom_first_arg, flag: bool) -> str:
        return "yes" if flag else "no"


def test_methods_classmethods_staticmethods_varied_receivers():
    svc = MultiReceiverService()

    # Classmethod validation
    assert MultiReceiverService.create_prefixed("test") == "GLOBAL:test"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `text`"
    ):
        MultiReceiverService.create_prefixed(123)

    # Staticmethod validation
    assert MultiReceiverService.calculate_hash(10) == (10 ^ 0x55AA)
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `val`"
    ):
        MultiReceiverService.calculate_hash("not_an_int")

    # Varied receiver names (this, me, ctx, custom_first_arg)
    assert svc.method_this(1, "hello") == "this:1:hello"
    with pytest.raises(TypeError, match="Type mismatch for typed variable `a`"):
        svc.method_this("bad", "hello")

    assert svc.method_me([10, 20, 30]) == 60
    with pytest.raises(
        TypeError, match=r"Type mismatch for typed variable `items"
    ):
        svc.method_me([10, "bad"])

    assert svc.method_ctx("timeout", 2.5) == "timeout=2.5"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `value`"
    ):
        svc.method_ctx("timeout", "not_a_float")

    assert svc.method_custom(True) == "yes"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `flag`"
    ):
        svc.method_custom(1)


# ---------------------------------------------------------------------------
# 5. Dunder Methods with Type Enforcement
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
class EnforcedContainer:
    def __init__(self, name: str):
        self.name = name
        self._store: dict[str, int] = {}

    def __setitem__(self, key: str, value: int) -> None:
        self._store[key] = value

    def __getitem__(self, key: str) -> int:
        return self._store[key]

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def __enter__(self) -> "EnforcedContainer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


def test_dunder_methods_enforcement():
    container = EnforcedContainer("main_store")
    container["cpu"] = 8
    container["memory"] = 32

    assert container["cpu"] == 8
    assert container["memory"] == 32
    assert len(container) == 2
    assert ("cpu" in container) is True
    assert ("gpu" in container) is False

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `key`"
    ):
        container[123] = 10

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `value`"
    ):
        container["disk"] = "500GB"

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `key`"
    ):
        _ = container[999]

    # Context manager protocol
    with container as ctx:
        assert ctx.name == "main_store"


# ---------------------------------------------------------------------------
# 6. Recursive & Self-Referencing Class Patterns
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
class HierarchyNode:
    def __init__(self, name: str):
        self.name = name
        self.parent: "HierarchyNode | None" = None
        self.children: list["HierarchyNode"] = []

    def attach_child(self, child: "HierarchyNode") -> None:
        child.parent = self
        self.children.append(child)

    def find_parent_name(self) -> str | None:
        if self.parent is not None:
            return self.parent.name
        return None


def test_recursive_tree_nodes():
    root = HierarchyNode("root")
    branch = HierarchyNode("branch")
    leaf = HierarchyNode("leaf")

    root.attach_child(branch)
    branch.attach_child(leaf)

    assert len(root.children) == 1
    assert len(branch.children) == 1
    assert leaf.find_parent_name() == "branch"
    assert branch.find_parent_name() == "root"
    assert root.find_parent_name() is None

    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `child`"
    ):
        root.attach_child("invalid_child_node")


# ---------------------------------------------------------------------------
# 7. Inheritance, Subclasses & Method Overriding with Super
# ---------------------------------------------------------------------------
@type_enforced.Enforcer
class BaseWorker:
    def execute(self, task_id: int, options: dict[str, str]) -> str:
        return f"base:{task_id}:{len(options)}"


class InheritedWorker(BaseWorker):
    # Unannotated child inheriting base class enforcement
    def extra_task(self, tag: str) -> str:
        return f"extra:{tag}"


@type_enforced.Enforcer
class OverridingWorker(BaseWorker):
    def execute(self, task_id: int, options: dict[str, str]) -> str:
        base_res = super().execute(task_id, options)
        return f"override:{base_res}"


def test_inheritance_and_super_calls():
    # Inherited worker still enforces base methods
    inherited = InheritedWorker()
    assert inherited.execute(1, {"timeout": "10"}) == "base:1:1"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `task_id`"
    ):
        inherited.execute("not_an_int", {"timeout": "10"})

    # Overriding worker calls super() cleanly
    overriding = OverridingWorker()
    assert overriding.execute(2, {"a": "1", "b": "2"}) == "override:base:2:2"
    with pytest.raises(
        TypeError, match=r"Type mismatch for typed variable `options"
    ):
        overriding.execute(2, {"a": 123})


# ---------------------------------------------------------------------------
# 8. Uninitialized Class References (type[T] / Type[T] / type[Union])
# ---------------------------------------------------------------------------
class ServiceA:
    pass


class ServiceB:
    pass


class ServiceC:
    pass


@type_enforced.Enforcer
class FactoryRegistry:
    def register_single(self, factory_cls: type[ServiceA]) -> str:
        return factory_cls.__name__

    def register_union(self, factory_cls: type[ServiceA | ServiceB]) -> str:
        return factory_cls.__name__

    def register_any(self, any_cls: type) -> str:
        return any_cls.__name__


def test_type_and_uninitialized_classes():
    registry = FactoryRegistry()

    # Exact class object passes
    assert registry.register_single(ServiceA) == "ServiceA"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `factory_cls`"
    ):
        registry.register_single(ServiceB)

    # Class instance fails when class object is expected
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `factory_cls`"
    ):
        registry.register_single(ServiceA())

    # Union of uninitialized classes
    assert registry.register_union(ServiceA) == "ServiceA"
    assert registry.register_union(ServiceB) == "ServiceB"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `factory_cls`"
    ):
        registry.register_union(ServiceC)

    # Unsubscripted type
    assert registry.register_any(int) == "int"
    assert registry.register_any(ServiceC) == "ServiceC"
    with pytest.raises(
        TypeError, match="Type mismatch for typed variable `any_cls`"
    ):
        registry.register_any("not_a_type")
