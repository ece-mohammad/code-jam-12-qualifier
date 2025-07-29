from __future__ import annotations

from dataclasses import dataclass, field
import re

from node import Node


@dataclass()
class Selector:
    """A dataclass to represent a query selector

    Attributes:
        tag_name: The tag name of the selector
        filter: A dictionary of attributes to match for the selector.
            - supports `id` and `class`. An `id` is a string, a `class` is a
            set of strings each representing a class.
    """

    __match_args__ = ("tag_name", "filter")

    tag_name: str = ""
    filter: dict[str, str | set[str]] = field(default_factory=dict)

    def __repr__(self):
        return "Selector(tag_name={}, filter={})".format(
            self.tag_name, self.filter
        )


def parse_selector_token(selector: str) -> Selector:
    """Given a selector token, returns a Selector object. Supports the following
    selectors:
        - `#id`
        - `.class`
        - `tag`
        - `tag.class`
        - `tag#id`
        - `tag.class#id`

    :param selector: A selector token eg `foo.bar#ham`
    :type selector: str
    :return: A Selector object
    :rtype: Selector
    """
    token_pattern = re.compile(r"(?P<token>(?P<lead>[#.])?[\w\-]+)")
    parsed_selector = Selector()

    for token in token_pattern.finditer(selector):
        if token.group("lead") == ".":
            if "class" in parsed_selector.filter:
                parsed_selector.filter["class"].add(
                    token.group("token")[1:]
                )
            else:
                parsed_selector.filter["class"] = {
                    token.group("token")[1:]
                }

        elif token.group("lead") == "#":
            parsed_selector.filter["id"] = token.group("token")[1:]

        else:
            parsed_selector.tag_name = token.group("token")

    return parsed_selector


def parse_query(query: str) -> list[Selector]:
    """Given a query, returns a list of Selector objects.
    :param query: A query string
    :type query: str
    :return: A list of Selector objects
    :rtype: list[Selector]
    """
    return [parse_selector_token(selector) for selector in query.split(",")]


def match_class(node: Node, class_set: set[str]) -> bool:
    """Returns True if the node has all the classes in the class_set, False
    otherwise.

    :param node: The node to match e.g. Node(tag='div', attributes={'class': 'container colour-primary'}, children=[...], text='')
    :type node: Node
    :param class_set: A set of classes to match e.g. {'container', 'colour-primary'}
    :type class_set: set[str]
    :return: True if the node has all the classes in the class_set, False otherwise
    :rtype: bool
    """
    if "class" not in node.attributes:
        return False
    node_classes = set(node.attributes["class"].split())
    return class_set.issubset(node_classes)


def match_id(node: Node, tag_id: str) -> bool:
    """Returns True if the node has the id tag_id, False otherwise.

    :param node: The node to match e.g. Node(tag='div', attributes={'id': 'topDiv', 'class': 'container'}, children=[...], text='')
    :type node: Node
    :param tag_id: The id to match e.g. 'container'
    :type tag_id: str
    :return: True if the node has the id tag_id, False otherwise
    :rtype: bool"""
    if "id" not in node.attributes:
        return False
    return node.attributes["id"] == tag_id


def match_selector(node: Node, selector: Selector) -> bool:
    """Matches a node to a selector, returns True if the node matches the
    selector, False otherwise.

    :param node: The node to match
    :type node: Node
    :param selector: The selector to match against
    :type selector: Selector
    :return: True if the node matches the selector, False otherwise
    :rtype: bool
    """

    if selector.tag_name and node.tag != selector.tag_name:
        return False

    if "class" in selector.filter and not match_class(
            node, selector.filter["class"]
    ):
        return False

    if "id" in selector.filter and not match_id(node, selector.filter["id"]):
        return False

    return True


def query_selector_all(node: Node, selector: str) -> list[Node]:
    """
    Given a node, the function will return all nodes, including children,
    that match the given selector.
    """

    matches: list[Node] = []

    for select in parse_query(selector):
        select_matches: list[Node] = []
        children: list[Node] = [node]
        seen_nodes_ids: set[int] = set()

        while children:
            child = children.pop()
            if match_selector(child, select) and id(child) not in seen_nodes_ids:
                select_matches.append(child)

            seen_nodes_ids.add(id(child))
            children.extend(child.children[::-1])
        matches.extend(select_matches)

    return matches


if __name__ == "__main__":
    node = Node(
        tag="div",
        attributes={"id": "topDiv"},
        children=[
            Node(
                tag="div",
                attributes={
                    "id"   : "innerDiv",
                    "class": "container colour-primary"
                },
                children=[
                    Node(tag="h1", text="This is a heading!"),
                    Node(
                        tag="p",
                        attributes={
                            "class": "colour-secondary",
                            "id"   : "innerContent"
                        },
                        text="I have some content within this container also!",
                    ),
                    Node(
                        tag="p",
                        attributes={
                            "class": "colour-secondary",
                            "id"   : "two"
                        },
                        text="This is another paragraph.",
                    ),
                    Node(
                        tag="p",
                        attributes={"class": "colour-secondary important"},
                        text="This is a third paragraph.",
                    ),
                    Node(
                        tag="a",
                        attributes={
                            "id"   : "home-link",
                            "class": "colour-primary button"
                        },
                        text="This is a button link.",
                    ),
                ],
            ),
            Node(
                tag="div",
                attributes={"class": "container colour-secondary"},
                children=[
                    Node(
                        tag="p",
                        attributes={"class": "colour-primary"},
                        text="This is a paragraph in a secondary container.",
                    ),
                ],
            ),
        ],
    )

    query = "p#two.colour-secondary, a#home-link.colour-primary.button"
    res = query_selector_all(node, query)
    print(res)
