import type_enforced

type_enforced.FastModuleEnforcer()


def process_list(items: list[int]) -> int:
    return len(items)


class Processor:
    def process_dict(self, d: dict[str, int]) -> int:
        return len(d)
