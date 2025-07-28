from __future__ import annotations

from dataclasses import dataclass, field
import re

from node import Node


@dataclass()
class Selector:
    """A dataclass to represent a query selector

    Attributes:
        tag_name: The tag name of the selector
        filter: A dictionary of attributes to match for the selector
    """

    __match_args__ = ("tag_name", "filter")

    tag_name: str = ""
    filter: dict[str, str | set[str]] = field(default_factory=dict)

    def repr__(self):
        return "Selector(tag_name={}, filter={}".format(
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
    return node_classes.intersection(class_set) == class_set


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
    selectors: list[Selector] = []
    children: list[Node] = [node]

    for selector_token in selector.split(", "):
        selectors.append(parse_selector_token(selector_token))

    while children:
        child = children.pop()
        for select in selectors:
            if match_selector(child, select):
                matches.append(child)

        children.extend(child.children[::-1])

    return matches
