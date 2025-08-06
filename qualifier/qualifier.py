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

Notes:

    1. The selector chain is reversed, so the first selector in the chain is
    the last selector in the DOM. For example, if the selector chain is
    `div h1 > p`, then the first selector in the chain is `p`, the second
    selector in the chain is `h1 >`, and the third selector in the chain is
    `div`. This is because matching nodes bottom up is more efficient than
    matching nodes top down. If we match top-down, when we match a node to the
    first selector in the chain, we have to check that all its children match
    the second selector in the chain, and if not, do they match the first
    selector in the chain? As a result, there are a lot of redundant checks.
    If we check bottom-up, when we match a node to the last selector in the
    chain, we have to check that all its parents match the preceding selectors
    in the chain. So we make extra checks for each node that matches the last
    selector in the chain. Which cuts down on the number of checks
    significantly.

    2. This implementation is not a complete implementation of the CSS
    specification, but it is enough to pass the qualifier. It implements the
    following CSS selectors:
        1. Tag selectors: `div`, `p`, etc.
        2. Class selectors: `.class-name`, `.class-name1.class-name2`, etc.
        3. ID selectors: `#id-name`, etc.
        4. Child selectors: `div > p`, `div p`, etc.
        5. Descendant selectors: `div p`, `div.container p`, etc.
        6. A subset of pseudo-classes:
            1. `:first-child`, `:last-child`, `:nth-child(n)`, etc.
            2. `:not(selector)` is partially implemented. It accepts only
                simple selectors e.g. tag names (`div`), classes (`.class`),
                ids (`#id`): `div`, `.class`, `#id`, etc. It doesn't accept
                complex selectors e.g. descendant selectors (`div p`), child
                selectors (`div > p`), pseudo-classes (`:nth-child(n)`), etc.

"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, IntEnum

from node import Node

_TAG_PATTERN = r"[a-zA-Z]\w{0,100}"
_CLASS_PATTERN = r"\.[-a-zA-Z][-\w]{0,100}"
_ID_PATTERN = r"#[-a-zA-Z][-\w]{0,100}"
_PSEUDO_CLASS_PATTERN = r":[a-zA-Z\-].{0,100}"

_TOKEN_PATTERN = re.compile(
    r"(?P<tag>{})|(?P<class>{})|(?P<id>{})|(?P<pclass>{})".format(
        _TAG_PATTERN,
        _CLASS_PATTERN,
        _ID_PATTERN,
        _PSEUDO_CLASS_PATTERN,
    )
)

_PSEUDO_CLASS_TOKEN_PATTERN = re.compile(
    r":(?P<type>[a-zA-Z\-]{1,100})(?P<argument>\([^)]{1,100}\))?"
)

_SPACE_PATTERN = re.compile(r"\s+")
_CHILD_PATTERN = re.compile(r"\s*>\s*")
_COMMA_PATTERN = re.compile(r"\s*,\s*")


class PseudoClassType(Enum):
    """
    A class that represents the different pseudo-classes that can be used in a
    CSS selector.

    Attributes:
        FIRST_CHILD (str): The first-child pseudo-class.
        LAST_CHILD (str): The last-child pseudo-class.
        NTH_CHILD (str): The nth-child pseudo-class.
        NOT (str): The not pseudo-class.
    """

    FIRST_CHILD = "first-child"
    LAST_CHILD = "last-child"
    NTH_CHILD = "nth-child"
    NOT = "not"


@dataclass
class PseudoClass:
    """Represents a CSS pseudo-class in a selector.

    Pseudo-classes are keywords that specify a special state of the selected
    elements. For example, :first-child selects the first child of its parent.

    Attributes:
        type (PseudoClassType): The type of pseudo-class.
        argument (str | int | SelectorChain | None): The argument for the
            pseudo-class, if any. For example:
            - For :nth-child(3), argument would be 3
            - For :not(.class), argument would be a SelectorChain
            - For :first-child, argument would be None
    """

    type: PseudoClassType
    argument: str | int | "SelectorChain" | None = None

    def __repr__(self):
        if self.argument is None:
            return "PseudoClass(type={})".format(self.type)

        return "PseudoClass(type={}, argument={})".format(
            self.type, self.argument
        )


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
    pseudo_class: PseudoClass | None = None

    def __repr__(self):
        return (
            "Selector(tag_name={}, filter={}, pseudo_class={}, "
            "relation={}, next={})"
        ).format(
            self.tag_name,
            self.filter,
            self.pseudo_class,
            self.relation_to_previous,
            self.next_selector,
        )


def parse_pseudo_class(pseudo_class: str) -> PseudoClass | None:
    """Parses a pseudo-class string into a PseudoClass object. The pseudo-class
    is a keyword that can be used to modify the behavior of a selector. For
    example, the :nth-child pseudo-class can be used to select the nth child
    of a node.

    The function handles the following pseudo-class types:
    - :first-child - Matches the first child of its parent
    - :last-child - Matches the last child of its parent
    - :nth-child(n) - Matches the nth child of its parent (1-based index)
    - :not(selector) - Matches elements not matching the given simple selector

    Args:
        pseudo_class (str): A pseudo-class string, e.g., `:nth-child(3)`.

    Returns:
        PseudoClass: A PseudoClass objects representing the parsed pseudo-
            class.
    """
    if not pseudo_class:
        return None

    token_type = None
    argument = None

    for token in _PSEUDO_CLASS_TOKEN_PATTERN.finditer(pseudo_class):
        try:
            token_type = PseudoClassType(token.group("type"))
        except ValueError:
            continue

        argument = token.group("argument")

        if token_type == PseudoClassType.NTH_CHILD:
            argument = int(argument[1:-1])

        elif token_type == PseudoClassType.NOT:
            argument = parse_selector_chain(argument[1:-1])

        else:
            argument = None

    if token_type is None:
        return None

    return PseudoClass(token_type, argument)


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
    parsed_selector = SelectorChain()

    for token in _TOKEN_PATTERN.finditer(selector_token):
        if token.group("tag"):
            parsed_selector.tag_name = token.group("tag")

        elif token.group("class"):
            if "class" not in parsed_selector.filter:
                parsed_selector.filter["class"] = set()
            parsed_selector.filter["class"].add(token.group("class")[1:])

        elif token.group("id"):
            parsed_selector.filter["id"] = token.group("id")[1:]

        elif token.group("pclass"):
            parsed_selector.pseudo_class = parse_pseudo_class(
                token.group("pclass")
            )

    return parsed_selector


def normalize_selector_chain(selector: str) -> str:
    """Normalizes a selector chain string by removing leading/trailing spaces,
    replacing multiple spaces with a single space, and formatting `>` as ` > `.

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
    spaced_selector = _SPACE_PATTERN.sub(" ", selector)
    return _CHILD_PATTERN.sub(" > ", spaced_selector)


def parse_selector_chain(selector: str) -> SelectorChain:
    """Parses a selector chain string into a SelectorChain object.

    The selector chain is built in reverse order (right-to-left) for more
    efficient matching. For example, "div > p" is stored as:
        `SelectorChain("p") -> SelectorChain("div") with relation
        IMMEDIATE_CHILD`

    Supported syntax:
    - Element selectors: "div", "p", etc.
    - Class selectors: ".class", "div.class"
    - ID selectors: "#id", "div#id"
    - Child combinators: ">"
    - Descendant combinators: " " (space)
    - Multiple classes: ".class1.class2"
    - Combined: "div#id.class1.class2"

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
        SelectorChain: A SelectorChain object representing the parsed selector
            chain.
    """
    selector = normalize_selector_chain(selector)

    parsed_selector = None
    selector_tokens = [tok.strip() for tok in selector.split() if tok]
    for token in selector_tokens:
        if token == ">":
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
        ... [
        ...   SelectorChain(tag_name="p",
        ...     relation=Relation.IMMEDIATE_CHILD,
        ...     next=SelectorChain(tag_name="div"))
        ... ]
        >>> parse_selector("div p")
        ... [
        ...   SelectorChain(tag_name="p",
        ...     relation=Relation.DESCENDANT,
        ...     next=SelectorChain(tag_name="div"))
        ... ]

    Args:
        query (str): A query string containing one or more selector chains.

    Returns:
        list[SelectorChain]: A list of SelectorChain objects representing the
            parsed selectors.
    """
    return [
        parse_selector_chain(selector)
        for selector in _COMMA_PATTERN.split(query)
    ]


def match_class_selector(node: Node, class_set: set[str]) -> bool:
    """Checks if a node has all the specified classes in the provided class
    set.

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
        class_set (set[str]): A set of class names to match against the node's
            classes.

    Returns:
        bool: True if the node has all the classes in the class_set, False
            otherwise.
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


def match_parent_selector(
    selector: SelectorChain, context: list[Node] | None = None
) -> bool:
    """Checks if the parent hierarchy matches the selector chain.

    This function verifies that the node's parent hierarchy matches the
    remaining selector chain. It handles both immediate child (>) and
    descendant ( ) relationships.

    Args:
        selector (SelectorChain): The remaining selector chain to match against
            the parent hierarchy.
        context (list[Node], optional): A list of parent nodes representing
            the current context. The first element is the direct parent.

    Returns:
        bool: True if the node and its parents match the selector chain, False
            otherwise.
    """
    parent_selector = selector.next_selector
    parents = deepcopy(context) if context else []

    if parent_selector is None:
        return True

    if not parents:
        return False

    if parent_selector.relation_to_previous == Relation.IMMEDIATE_CHILD:
        immediate_parent = parents.pop()
        if not match_selector(
            immediate_parent, parent_selector, context=parents
        ):
            return False
    else:
        while parents:
            parent = parents.pop()
            if match_selector(parent, parent_selector, context=parents):
                break
        else:
            return False

    return True and match_parent_selector(parent_selector, parents)


def match_first_child_pseudo_class_selector(
    node: Node, context: list[Node]
) -> bool:
    """Checks if a node is the first child of its parent.

    Args:
        node (Node): The node to check.
        context (list[Node]): A list of parent nodes representing the context.

    Returns:
        True if the node is the first child of its parent, False otherwise.
    """
    if not context:
        return False

    parent = context[-1]
    return node == parent.children[0]


def match_last_child_pseudo_class_selector(
    node: Node, context: list[Node]
) -> bool:
    """Checks if a node is the last child of its parent.

    Args:
        node (Node): The node to check.
        context (list[Node]): A list of parent nodes representing the context.

    Returns:
        True if the node is the last child of its parent, False otherwise.
    """
    if not context:
        return False

    parent = context[-1]
    return node == parent.children[-1]


def match_nth_child_pseudo_class_selector(
    node: Node, index: int, context: list[Node]
) -> bool:
    """Checks if a node is the nth child of its parent.

    Args:
        node (Node): The node to check.
        index (int): The index of the child to check.
        context (list[Node]): A list of parent nodes representing the context.

    Returns:
        True if the node is the nth child of its parent, False otherwise.
    """
    if not context:
        return False

    parent = context[-1]
    return (
        0 < index <= len(parent.children)
        and node == parent.children[index - 1]
    )


def match_not_pseudo_class_selector(
    node: Node, selector: SelectorChain, context: list[Node] | None = None
) -> bool:
    """Checks if a node does not match a selector.

    Args:
        node (Node): The node to check.
        selector (SelectorChain): The selector to check against.
        context (list[Node], optional): A list of parent nodes representing
            the context. Defaults to None.

    Returns:
        True if the node does not match the selector, False otherwise.
    """
    copy_selector = deepcopy(selector)
    copy_selector.next_selector = None
    copy_selector.relation_to_previous = Relation.DESCENDANT
    return not match_selector(node, selector, context)


def match_pseudo_class_selector(
    node: Node, selector: SelectorChain, context: list[Node] | None = None
) -> bool:
    """Checks if a node matches a pseudo-class selector.

    Args:
        node (Node): The node to check.
        selector (SelectorChain): The selector to check against.
        context (list[Node], optional): A list of parent nodes representing
            the context. Defaults to None.

    Returns:
        True if the node matches the pseudo-class selector, False otherwise.
    """

    pseudo_class = selector.pseudo_class
    parent_node = context[-1] if context else None

    if not pseudo_class:
        return True

    if parent_node:
        if pseudo_class.type == PseudoClassType.FIRST_CHILD:
            return match_first_child_pseudo_class_selector(node, context)

        if pseudo_class.type == PseudoClassType.LAST_CHILD:
            return match_last_child_pseudo_class_selector(node, context)

        if pseudo_class.type == PseudoClassType.NTH_CHILD:
            return match_nth_child_pseudo_class_selector(
                node, pseudo_class.argument, context
            )

        if pseudo_class.type == PseudoClassType.NOT:
            return match_not_pseudo_class_selector(
                node, pseudo_class.argument, context
            )

    return False


def match_selector(
    node: Node, selector: SelectorChain, context: list[Node] | None = None
) -> bool:
    """Matches a node against a single selector, returning True if the node
    matches the selector's tag name, class, and id, False otherwise.

    Args:
        node (Node): The node to match.
        selector (SelectorChain): The selector to match against.
        context (list[Node], optional): A list of parent nodes representing
            the context, used for matching pseudo-classes. Defaults to None.

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

    return match_pseudo_class_selector(node, selector, context)


def match_selector_chain(
    node: Node,
    selector_chain: SelectorChain,
    context: list[Node] | None = None,
) -> list[Node]:
    """Matches a node and its descendants against a selector chain, returning
    all matching nodes.

    This function performs a depth-first search of the DOM tree starting from
    the given node. For each node, it checks if it matches the selector chain
    and its parent hierarchy matches the rest of the chain.

    Args:
        node (Node): The root node to start matching from.
        selector_chain (SelectorChain): The selector chain to match against.
        context (list[Node], optional): A list of parent nodes as context.
            Defaults to None.

    Returns:
        list[Node]: A list of nodes that match the selector chain.
    """

    matches = []
    matches_ids = set()
    parents = deepcopy(context) or []

    if match_selector(
        node, selector_chain, context=parents
    ) and match_parent_selector(selector_chain, context=parents):
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

    This is the main entry point for the CSS selector engine. It handles:
    - Splitting multiple selectors by comma
    - Removing duplicate matches

    Args:
        node (Node): The root node to start the search from.
        selector (str): The selector string to match nodes against.

    Returns:
        list[Node]: A list of all unique nodes that match the provided
            selector.
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
                    "id": "innerDiv",
                    "class": "container colour-primary",
                },
                children=[
                    Node(tag="h1", text="This is a heading!"),
                    Node(
                        tag="p",
                        attributes={
                            "class": "colour-secondary",
                            "id": "innerContent",
                        },
                        text="I have some content within this container also!",
                    ),
                    Node(
                        tag="p",
                        attributes={"class": "colour-secondary", "id": "two"},
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
                            "id": "home-link",
                            "class": "colour-primary button",
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

    query = "div:nth-child(1) > p"
    res = query_selector_all(node, query)
    print(*res, sep="\n")
