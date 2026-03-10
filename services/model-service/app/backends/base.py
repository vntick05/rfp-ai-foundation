from dataclasses import dataclass


@dataclass(frozen=True)
class BackendDescriptor:
    name: str
    api_style: str
    gpu_capable: bool
    implemented: bool
