#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
qualifier.py

CSS-like query selector implementation in Python for PyJam 2025 qualifier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import re

from node import Node


class Relation(IntEnum):
    """
    An enum to represent the relation between two selectors in
    a selector chain. The relation is used to determine if a node
    is an immediate child or descendant of another node.

    Attributes:
        IMMEDIATE_CHILD: The first selector is an immediate child of the second.
        DESCENDANT: The first selector is a descendant of the second.
    """
    IMMEDIATE_CHILD = 0
    DESCENDANT = 1


@dataclass()
class SelectorChain:
    """A dataclass to represent a query selector chain. A selector chain is a
    sequence of selectors that are chained together using the `>` or ` `
    operators. Each term in the chain is a selector that can be used to match
    nodes in the DOM.

    Attributes:
        tag_name: The tag name of the selector
        filter: A dictionary of attributes to match for the selector.
            - supports `id` and `class`. An `id` is a string, a `class` is a
            set of strings each representing a class.
        next: The next selector in the chain
        relation: The relation between the current selector and the next selector
    """

    tag_name: str = ""
    filter: dict[str, str | set[str]] = field(default_factory=dict)
    next: SelectorChain | None = None
    relation: Relation = Relation.DESCENDANT

    def __repr__(self):
        return "Selector(tag_name={}, filter={}, relation={}, next={})".format(
            self.tag_name,
            self.filter,
            self.relation,
            self.next,
        )


def parse_selector_token(selector_token: str) -> SelectorChain:
    """Given a selector token, returns a Selector object. Supports the following
    selectors:
        - `#id`
        - `.class`
        - `tag`
        - `tag.class`
        - `tag#id`
        - `tag.class#id`

    Example:

    >>> parse_selector_token("div h1 > p")
    ... SelectorChain(
    ...   tag_name="p",
    ...   relation=Relation.DESCENDANT,
    ...     next=SelectorChain(
    ...     tag_name="h1",
    ...     relation=Relation.IMMEDIATE_CHILD,
    ...     next=SelectorChain(
    ...        tag_name="div", relation=Relation.DESCENDANT)
    ...   )
    ... )

    :param selector_token: A selector token eg `foo.bar#ham`
    :type selector_token: str
    :return: A Selector object
    :rtype: SelectorChain
    """
    token_pattern = re.compile(r"(?P<token>(?P<lead>[#.> ])?[\w\-]+)")
    parsed_selector = SelectorChain()

    for token in token_pattern.finditer(selector_token):
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


def normalize_selector_chain(selector: str) -> str:
    """Given a selector, returns a normalized selector chain, which is
    a string of selectors separated by `>` and/or spaces or ` `. The selector
    chain is normalized in the following ways:
        - leading and trailing spaces are removed
        - multiple spaces are replaced with a single space
        - `>` is replaced with ` > `

    Examples:

    >>> normalize_selector_chain("div   p")
    ... "div p"
    >>> normalize_selector_chain("div>p")
    ... "div > p"
    >>> normalize_selector_chain("div  >  p")
    ... "div > p"

    :param selector: A selector chain eg `div h1 > p`
    :type selector: str
    :return: A normalized selector
    :rtype: str
    """
    space_pattern = re.compile(r"\s+")
    pattern = re.compile(r"\s*>\s*")
    spaced_selector = space_pattern.sub(" ", selector)
    return pattern.sub(" > ", spaced_selector)


def parse_selector_chain(selector: str) -> SelectorChain:
    """Given a selector chain, returns a SelectorChain object. Supports the
    following selectors:
        - `#id`
        - `.class`
        - `tag`
        - `tag.class`
        - `tag#id`
        - `tag.class#id`
        - `tag.class#id > tag.class#id`
        - `tag.class#id tag.class#id`

    Examples:

    >>> parse_selector_chain("div h1 > p")
    ... SelectorChain(
    ...   tag_name="p",
    ...   relation=Relation.IMMEDIATE_CHILD,
    ...     next=SelectorChain(
    ...     tag_name="h1",
    ...     relation=Relation.DESCENDANT,
    ...     next=SelectorChain(tag_name="div")
    ...   )
    ... )

    :param selector: A selector chain eg `div h1 > p`
    :type selector: str
    :return: A Selector chain object
    :rtype: SelectorChain
    """

    selector = normalize_selector_chain(selector)

    parsed_selector = None
    selector_tokens = [
        tok.strip()
        for tok in re.split(r"\s+", selector) if tok
    ]
    for token in selector_tokens:
        if token == '>':
            parsed_selector.relation = Relation.IMMEDIATE_CHILD
            continue

        current_selector = parse_selector_token(token)
        current_selector.next = parsed_selector
        parsed_selector = current_selector

    return parsed_selector


def parse_selector(query: str) -> list[SelectorChain]:
    """Given a query, returns a list of Selector chain objects.

    Examples:

    >>> parse_selector("div, p")
    ... [SelectorChain(tag_name="div"), SelectorChain(tag_name="p")]
    >>> parse_selector("div > p")
    ... [SelectorChain(tag_name="p", relation=Relation.IMMEDIATE_CHILD, next=SelectorChain(tag_name="div"))]
    >>> parse_selector("div p")
    ... [SelectorChain(tag_name="p", relation=Relation.DESCENDANT, next=SelectorChain(tag_name="div"))]

    :param query: A query string
    :type query: str
    :return: A list of Selector objects
    :rtype: list[SelectorChain]
    """
    return [
        parse_selector_chain(selector)
        for selector in re.split(r"\s*,\s*", query)
    ]


def match_class_selector(node: Node, class_set: set[str]) -> bool:
    """Returns True if the node has all the classes in the class_set, False
    otherwise.

    Examples:

    >>> match_class_selector(
    ...   Node(tag='div',
    ...     attributes={'class': 'container colour-primary'},
    ...     children=[...], text=''),
    ...   {'container', 'colour-primary'}
    ... )
    ... True

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


def match_id_selector(node: Node, tag_id: str) -> bool:
    """Returns True if the node has the id tag_id, False otherwise.

    Examples:

    >>> match_id_selector(
    ...   Node(tag='div',
    ...     attributes={'id': 'topDiv', 'class': 'container'},
    ...     children=[...], text=''),
    ...   'topDiv'
    ... )
    ... True

    :param node: The node to match e.g. Node(tag='div', attributes={'id': 'topDiv', 'class': 'container'}, children=[...], text='')
    :type node: Node
    :param tag_id: The id to match e.g. 'container'
    :type tag_id: str
    :return: True if the node has the id tag_id, False otherwise
    :rtype: bool"""
    if "id" not in node.attributes:
        return False
    return node.attributes["id"] == tag_id


def match_parent_selector(selector: SelectorChain, context: list[Node] = None) -> bool:
    """Matches a node and its parents to a selector chain, returns True if the
    node and its parents match the selector chain, False otherwise.

    :param selector: The selector chain to match against
    :type selector: SelectorChain
    :param context: The context to match against (a list of parent nodes)
    :type context: Node
    :return: True if the node and its parents match the selector chain, False otherwise
    :rtype: bool
    """
    parent_selector = selector.next
    parents = context

    if parent_selector is None:
        return True

    if not parents:
        return False

    if parent_selector.relation == Relation.IMMEDIATE_CHILD:
        immediate_parent = parents.pop()
        if not match_selector(immediate_parent, parent_selector):
            return False
    else:
        while parents:
            parent = parents.pop()
            if match_selector(parent, parent_selector):
                break
        else:
            return False

    return True and match_parent_selector(parent_selector, parents)

def match_selector(node: Node, selector: SelectorChain) -> bool:
    """Matches a node to a selector, returns True if the node matches the
    selector, False otherwise.

    :param node: The node to match
    :type node: Node
    :param selector: The selector to match against
    :type selector: SelectorChain
    :return: True if the node matches the selector, False otherwise
    :rtype: bool
    """

    if selector.tag_name and node.tag != selector.tag_name:
        return False

    if "class" in selector.filter and not match_class_selector(
            node, selector.filter["class"]
    ):
        return False

    if "id" in selector.filter and not match_id_selector(
            node, selector.filter["id"]
    ):
        return False

    return True


def match_selector_chain(node: Node, selector_chain: SelectorChain, context=None) -> list[Node]:
    """
    Given a node and a selector chain, returns a list of nodes that match the
    selector chain.

    @see Node
    @see SelectorChain

    :param node: The node to match
    :type node: Node
    :param selector_chain: The selector chain to match against
    :type selector_chain: SelectorChain
    :return: A list of nodes that match the selector chain
    :rtype: list[Node]
    """

    matches = []
    matches_ids = set()
    parents = context or []

    if (match_selector(node, selector_chain) and
        match_parent_selector(selector_chain, context=parents[::])):
        matches_ids.add(id(node))
        matches.append(node)

    parents.append(node)
    for child in node.children:
        for match in match_selector_chain(child, selector_chain, parents):
            if id(match) not in matches_ids:
                matches.append(match)
                matches_ids.add(id(match))
    parents.pop()
    return matches


def query_selector_all(node: Node, selector: str) -> list[Node]:
    """
    Given a node, the function will return all nodes, including children,
    that match the given selector.
    """

    matches: list[Node] = []
    matches_ids: set[int] = set()

    for selector_chain in parse_selector(selector):
        select_matches: list[Node] = match_selector_chain(node, selector_chain)

        for match in select_matches:
            match_id = id(match)
            if match_id not in matches_ids:
                matches_ids.add(match_id)
                matches.append(match)

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

    query = "div > .colour-primary"
    res = query_selector_all(node, query)
    print(*res, sep="\n")
