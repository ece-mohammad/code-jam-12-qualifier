#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
qualifier.py

CSS-like query selector implementation in Python for PyJam 2025 qualifier.

This isn't a complete implementation of the CSS specification, but it is
enough to pass the qualifier. The implementation is based on the specification
at:
    - https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Selectors
    - https://github.com/fb55/css-select

This implementation of the `query_selector_all` function, which accepts a Node
instance and a string as inputs, and returns a list of Node instances that
match the given selector.

The implementation does the following:

    1. Parse the selector string into a list of individual selector, by
    splitting the selector string around commas. For example: selector string
    `div, p`, then we have 2 individual selectors: `div` and `p`.

    2. For each selector in the list of individual selectors:
        1. Parse the selector into a selector chain, which is a linked list of
        selectors that are chained together using the `>` or ` ` operators
        to represent hierarchy. For example: selector string : `div > p`,
        then we have to match a `p` node that is an immediate child of
        a `div` node.

        2. For each node in the DOM, if the node matches the selector chain,
        then add the node to the list of nodes that match the selector chain.

    3. Return the list of nodes that match the selector chain.

Note:

    The selector chain is reversed, so the first selector in the chain is the
    last selector in the DOM. For example, if the selector chain is
    `div h1 > p`, then the first selector in the chain is `p`, the second
    selector in the chain is `h1 > p`, and the third selector in the chain is
    `div`.
    This is because mathing nodes bottom up is more efficient than matching
    nodes top down. Because if we match top-down, when we match a node to the
    first selector in the chain, we have to check that all its children match
    the second selector in the chain, and if not, do they match the first
    selector in the chain? As a result, there are a lot of redundant checks.

    If we check bottom-up, when we match a node to the last selector in the
    chain, we have to check that all its parents match the preceding selectors
    in the chain. So we make extra checks for each node that matches the last
    selector in the chain. Which cuts down on redundant checks significantly.

"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import IntEnum
import re

from node import Node


class Relation(IntEnum):
    """An enum to represent the relation between two selectors in a selector
    chain. The relation is used to determine if a node is an immediate child
    or descendant of another node.

    Attributes:
        IMMEDIATE_CHILD (int): The first selector is an immediate child of
            the second.
        DESCENDANT (int): The first selector is a descendant of the second.
    """
    IMMEDIATE_CHILD = 0
    DESCENDANT = 1


@dataclass()
class SelectorChain:
    """A dataclass to represent a query selector chain. A selector chain is a
    sequence of selectors that are chained together using the `>` or ` `
    operators. Each term in the chain is a selector that can be used to match
    nodes in the DOM. The `>` operator is used to match immediate child nodes,
    while the ` ` operator is used to match descendant nodes.

    Attributes:
        tag_name (str): The tag name of the selector.
        filter (dict[str, str | set[str]]): A dictionary of attributes to match
            for the selector. Supports `id` (string) and `class`
            (set of strings representing classes).
        next_selector (SelectorChain | None): The next selector in the chain.
        relation_to_previous (Relation): The relation between the current
            selector and the next selector. The default value is
            Relation.DESCENDANT.
    """
    tag_name: str = ""
    filter: dict[str, str | set[str]] = field(default_factory=dict)
    next_selector: SelectorChain | None = None
    relation_to_previous: Relation = Relation.DESCENDANT

    def __repr__(self):
        return "Selector(tag_name={}, filter={}, relation={}, next={})".format(
            self.tag_name,
            self.filter,
            self.relation_to_previous,
            self.next_selector,
        )


def parse_selector_token(selector_token: str) -> SelectorChain:
    """Parses a selector token into a SelectorChain object. Supports the
    following selectors: `#id`, `.class`, `tag`, `tag.class`, `tag#id`,
    and `tag.class#id`.

    Examples:
        >>> parse_selector_token("div h1 > p")
        ... SelectorChain(
        ...   tag_name="p",
        ...   relation_to_previous=Relation.DESCENDANT,
        ...     next=SelectorChain(
        ...     tag_name="h1",
        ...     relation_to_previous=Relation.IMMEDIATE_CHILD,
        ...     next=SelectorChain(
        ...        tag_name="div", relation_to_previous=Relation.DESCENDANT)
        ...   )
        ... )

    Args:
        selector_token (str): A selector token, e.g., `div h1 > p`.

    Returns:
        SelectorChain: A SelectorChain object representing the selector token.
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
    """Normalizes a selector chain string by removing leading/trailing spaces, replacing
    multiple spaces with a single space, and formatting `>` as ` > `.

    Examples:
        >>> normalize_selector_chain("div   p")
        ... "div p"
        >>> normalize_selector_chain("div>p")
        ... "div > p"
        >>> normalize_selector_chain("div  >  p")
        ... "div > p"

    Args:
        selector (str): A selector chain, e.g., `div h1 > p`.

    Returns:
        str: A normalized selector chain string.
    """
    space_pattern = re.compile(r"\s+")
    pattern = re.compile(r"\s*>\s*")
    spaced_selector = space_pattern.sub(" ", selector)
    return pattern.sub(" > ", spaced_selector)


def parse_selector_chain(selector: str) -> SelectorChain:
    """Parses a selector chain string into a SelectorChain object. Supports selectors like
    `#id`, `.class`, `tag`, `tag.class`, `tag#id`, `tag.class#id`, and chained selectors
    with `>` or spaces.

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

    Args:
        selector (str): A selector chain, e.g., `div h1 > p`.

    Returns:
        SelectorChain: A SelectorChain object representing the parsed selector chain.
    """
    selector = normalize_selector_chain(selector)

    parsed_selector = None
    selector_tokens = [
        tok.strip()
        for tok in re.split(r"\s+", selector) if tok
    ]
    for token in selector_tokens:
        if token == '>':
            parsed_selector.relation_to_previous = Relation.IMMEDIATE_CHILD
            continue

        current_selector = parse_selector_token(token)
        current_selector.next_selector = parsed_selector
        parsed_selector = current_selector

    return parsed_selector


def parse_selector(query: str) -> list[SelectorChain]:
    """Parses a query string into a list of SelectorChain objects.

    Examples:
        >>> parse_selector("div, p")
        ... [SelectorChain(tag_name="div"), SelectorChain(tag_name="p")]
        >>> parse_selector("div > p")
        ... [SelectorChain(tag_name="p", relation=Relation.IMMEDIATE_CHILD, next=SelectorChain(tag_name="div"))]
        >>> parse_selector("div p")
        ... [SelectorChain(tag_name="p", relation=Relation.DESCENDANT, next=SelectorChain(tag_name="div"))]

    Args:
        query (str): A query string containing one or more selector chains.

    Returns:
        list[SelectorChain]: A list of SelectorChain objects representing the parsed selectors.
    """
    return [
        parse_selector_chain(selector)
        for selector in re.split(r"\s*,\s*", query)
    ]


def match_class_selector(node: Node, class_set: set[str]) -> bool:
    """Checks if a node has all the specified classes in the provided class set.

    Examples:
        >>> match_class_selector(
        ...   Node(tag='div',
        ...     attributes={'class': 'container colour-primary'},
        ...     children=[...], text=''),
        ...   {'container', 'colour-primary'}
        ... )
        ... True

    Args:
        node (Node): The node to check for matching classes.
        class_set (set[str]): A set of class names to match against the node's classes.

    Returns:
        bool: True if the node has all the classes in the class_set, False otherwise.
    """
    if "class" not in node.attributes:
        return False
    node_classes = set(node.attributes["class"].split())
    return class_set.issubset(node_classes)


def match_id_selector(node: Node, tag_id: str) -> bool:
    """Checks if a node has the specified ID.

    Examples:
        >>> match_id_selector(
        ...   Node(tag='div',
        ...     attributes={'id': 'topDiv', 'class': 'container'},
        ...     children=[...], text=''),
        ...   'topDiv'
        ... )
        ... True

    Args:
        node (Node): The node to check for a matching ID.
        tag_id (str): The ID to match against the node's ID.

    Returns:
        bool: True if the node's ID matches the provided ID, False otherwise.
    """
    if "id" not in node.attributes:
        return False
    return node.attributes["id"] == tag_id


def match_parent_selector(selector: SelectorChain, context: list[Node] = None) -> bool:
    """Matches a node and its parents against a selector chain.

    Args:
        selector (SelectorChain): The selector chain to match against.
        context (list[Node], optional): A list of parent nodes representing the context.
            Defaults to None.

    Returns:
        bool: True if the node and its parents match the selector chain, False otherwise.
    """
    parent_selector = selector.next_selector
    parents = deepcopy(context) if context else []

    if parent_selector is None:
        return True

    if not parents:
        return False

    if parent_selector.relation_to_previous == Relation.IMMEDIATE_CHILD:
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
    """Matches a node against a single selector, returning True if the node
    matches the selector's tag name, class, and id, False otherwise.

    Args:
        node (Node): The node to match.
        selector (SelectorChain): The selector to match against.

    Returns:
        bool: True if the node matches the selector, False otherwise.
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


def match_selector_chain(
    node: Node, selector_chain: SelectorChain,
    context: list[Node] | None = None) -> list[Node]:
    """Matches a node and its descendants against a selector chain, returning
    all matching nodes.

    Args:
        node (Node): The root node to start matching from.
        selector_chain (SelectorChain): The selector chain to match against.
        context (list[Node], optional): A list of parent nodes as context. Defaults to None.

    Returns:
        list[Node]: A list of nodes that match the selector chain.
    """

    matches = []
    matches_ids = set()
    parents = deepcopy(context) or []

    if (match_selector(node, selector_chain) and
            match_parent_selector(selector_chain, context=parents)):
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
    """Retrieves all nodes (including children) that match the given selector
    string.

    Args:
        node (Node): The root node to start the search from.
        selector (str): The selector string to match nodes against.

    Returns:
        list[Node]: A list of all nodes that match the provided selector.
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
