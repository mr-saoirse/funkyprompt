import typing
from funkyprompt.ops.utils.inspector import inspect_modules_for_class_types

from pydantic import BaseModel, Field


class DiagramRequest(BaseModel):
    domains: typing.List[str]
    categories: typing.Optional[typing.List[str]]


from enum import Enum


class DiagramDomains(Enum):
    k8s = "k8s"
    gcp = "gcp"
    aws = "aws"
    programming = "programming"


def draw_diagram_preparation_for_domains(diagram_domain: DiagramDomains):
    # You can search for more details about K8s by calling the function X
    """
    Use this function to help you draw a diagram by passing in at least one domain.
    After calling this function you should provide the python code that generates the diagram.
    To generate a diagram you need to know two things:
    1. an example program for generating diagrams for the given domain(s)
    2. the fully qualified names of entities to use in diagrams in those domains
    Calling this function with the domains e,g k8s for Kubernetes will give you the data you need.

    ** Args **
        diagram_domain: A request for diagrams using domains from the enumeration of choices provided

    ** Returns **
       a list of fully qualified diagram elements to use in drawing e.g.  k8s.controlplane.CCM,
    """

    import diagrams

    def iterator():
        for namespace, object_name, object in inspect_modules_for_class_types(
            diagrams, diagrams.Node
        ):
            # if any(d.lower() in namespace for d in diagram_request.domains):
            # strings will be passed by the LLM but we can test with raw vals
            if str(diagram_domain) == namespace:
                # if categories:
                #     if any(c.lower() in namespace for c in categories):
                #         yield f"{namespace}.{object}"
                # else:
                yield f"{namespace}.{object_name}"

    elements = list(iterator())
    example = """
        from diagrams import Cluster, Diagram
        from diagrams.k8s.compute import Pod, StatefulSet
        from diagrams.k8s.network import Service
        from diagrams.k8s.storage import PV, PVC, StorageClass
        # Create a diagram titled "Stateful Architecture" and hide it initially
        with Diagram("Stateful Architecture", show=False) as g:
            # Create a cluster labeled "Apps"
            with Cluster("Apps"):
                svc = Service("svc")
                sts = StatefulSet("sts")
                apps = []
                for _ in range(3):
                    # Create a Pod component named "pod"
                    pod = Pod("pod")
                    apps.append(svc >> pod >> pvc)
            # Create connections from Persistent Volume (PV) and StorageClass (sc) to the Apps cluster
            apps << PV("pv") << StorageClass("sc")"""

    return {"example": example, "elements": elements}
