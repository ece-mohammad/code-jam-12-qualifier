"""
Test cases for the query_selector_all function
"""


import unittest

from node import Node
import qualifier

solution = qualifier.query_selector_all


class TestQuerySelector(unittest.TestCase):

    def setUp(self):
        self.node_test1 = Node(
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

    def test_tag(self):
        node = self.node_test1
        result = solution(node, "div")
        answer = [node, node.children[0], node.children[1]]
        self.assertCountEqual(result, answer)

    def test_id(self):
        node = self.node_test1
        result = solution(node, "#innerDiv")
        answer = [node.children[0]]
        self.assertCountEqual(result, answer)

    def test_class(self):
        node = self.node_test1
        result = solution(node, ".colour-primary")
        answer = [
            node.children[0],
            node.children[0].children[4],
            node.children[1].children[0],
        ]
        self.assertCountEqual(result, answer)

    # Test compound selector
    def test_tag_class(self):
        node = self.node_test1
        result = solution(node, "p.colour-secondary")
        answer = [
            node.children[0].children[1],
            node.children[0].children[2],
            node.children[0].children[3],
        ]
        self.assertCountEqual(result, answer)

    def test_tag_id(self):
        node = self.node_test1
        result = solution(node, "div#innerDiv")
        answer = [node.children[0]]
        self.assertCountEqual(result, answer)

    def test_id_class(self):
        node = self.node_test1
        result = solution(node, "#innerContent.colour-secondary")
        answer = [node.children[0].children[1]]
        self.assertCountEqual(result, answer)

    def test_tag_id_class(self):
        node = self.node_test1
        result = solution(node, "div#innerDiv.colour-primary")
        answer = [node.children[0]]
        self.assertCountEqual(result, answer)

    def test_multi_class(self):
        node = self.node_test1
        result = solution(node, ".colour-primary.button")
        answer = [node.children[0].children[4]]
        self.assertCountEqual(result, answer)

    def test_tag_multi_class(self):
        node = self.node_test1
        result = solution(node, "#home-link.colour-primary.button")
        answer = [node.children[0].children[4]]
        self.assertCountEqual(result, answer)

    def test_tag_id_multi_class(self):
        node = self.node_test1
        result = solution(node, "a#home-link.colour-primary.button")
        answer = [node.children[0].children[4]]
        self.assertCountEqual(result, answer)

    # Test multiple selectors
    def test_multi_selector(self):
        node = self.node_test1
        result = solution(node, "#topDiv, h1, .colour-primary")
        answer = [
            node,
            node.children[0],
            node.children[0].children[0],
            node.children[0].children[4],
            node.children[1].children[0],
        ]
        self.assertCountEqual(result, answer)

    def test_multi_selector_compound(self):
        node = self.node_test1
        result = solution(node, "h1, a#home-link.colour-primary.button")
        answer = [node.children[0].children[0], node.children[0].children[4]]
        self.assertCountEqual(result, answer)

    def test_compound_multi_selector_compound(self):
        node = self.node_test1
        result = solution(
            node, "p#two.colour-secondary, a#home-link.colour-primary.button"
        )
        answer = [node.children[0].children[2], node.children[0].children[4]]
        self.assertCountEqual(result, answer)

    # Test absence
    def test_absent_tag(self):
        node = self.node_test1
        result = solution(node, "i")
        answer = []
        self.assertEqual(result, answer)

    def test_absent_id(self):
        node = self.node_test1
        result = solution(node, "#badID")
        answer = []
        self.assertEqual(result, answer)

    def test_absent_class(self):
        node = self.node_test1
        result = solution(node, ".missing-class")
        answer = []
        self.assertEqual(result, answer)

    def test_multi_absent(self):
        node = self.node_test1
        result = solution(node, "i, #badID, .missing-class")
        answer = []
        self.assertEqual(result, answer)

    def test_mixed_absent(self):
        node = self.node_test1
        result = solution(node, "h1, #badID, .missing-class")
        answer = [node.children[0].children[0]]
        self.assertCountEqual(result, answer)

    def test_mixed_absent_compound(self):
        node = self.node_test1
        result = solution(
            node,
            "li#random.someclass, a#home-link, div, .colour-primary.badclass"
        )
        answer = [
            node,
            node.children[0],
            node.children[0].children[4],
            node.children[1],
        ]
        self.assertCountEqual(result, answer)


class TestBonus(unittest.TestCase):
    def setUp(self):
        """
        <div id="topDiv">
            <div id="innerDiv" class="container colour-primary">
                <h1>This is a heading!</h1>
                <p id="innerContent" class="colour-secondary">I have some content within this container also!</p>
                <p id="two" class="colour-secondary">This is another paragraph.</p>
                <p class="colour-secondary important">This is a third paragraph.</p>
                <a id="home-link" class="colour-primary button">This is a button link.</a>
            </div>
            <div class="container colour-secondary">
                <p class="colour-primary">This is a paragraph in a secondary container.</p>
            </div>
        </div>
        """
        self.node_test1 = Node(
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

    def test_immediate_child(self):
        node = self.node_test1
        result = solution(node, "div > div")
        expected = [node.children[0], node.children[1]]
        self.assertCountEqual(result, expected)

    def test_descendant(self):
        node = self.node_test1
        result = solution(node, "div p")
        expected = [
            node.children[0].children[1],
            node.children[0].children[2],
            node.children[0].children[3],
            node.children[1].children[0],
        ]
        self.assertCountEqual(result, expected)

    def test_descendant_single_level(self):
        node = self.node_test1
        result = solution(node, "div h1")
        expected = [node.children[0].children[0]]
        self.assertCountEqual(result, expected)

    def test_descendant_multi_level(self):
        node = self.node_test1
        result = solution(node, "div a")
        expected = [node.children[0].children[4]]
        self.assertCountEqual(result, expected)

    def test_immediate_child_single(self):
        node = self.node_test1
        result = solution(node, "div > h1")
        expected = [node.children[0].children[0]]
        self.assertCountEqual(result, expected)

    def test_immediate_child_none(self):
        node = self.node_test1
        result = solution(node, "div > h2")
        expected = []
        self.assertCountEqual(result, expected)

    def test_descendant_multiple_matches(self):
        node = self.node_test1
        result = solution(node, "div p")
        expected = [
            node.children[0].children[1],
            node.children[0].children[2],
            node.children[0].children[3],
            node.children[1].children[0],
        ]
        self.assertCountEqual(result, expected)

    def test_immediate_child_multiple(self):
        node = self.node_test1
        result = solution(node, "div > div")
        expected = [node.children[0], node.children[1]]
        self.assertCountEqual(result, expected)

    def test_immediate_child_chain(self):
        node = self.node_test1
        result = solution(node, "div > div > a")
        expected = [node.children[0].children[4]]
        self.assertCountEqual(result, expected)

    def test_descendant_then_immediate_child(self):
        node = self.node_test1
        result = solution(node, "div div > p")
        expected = [
            node.children[0].children[1],
            node.children[0].children[2],
            node.children[0].children[3],
            node.children[1].children[0],
        ]
        self.assertCountEqual(result, expected)

    def test_immediate_child_then_descendant(self):
        node = self.node_test1
        result = solution(node, "div > div p")
        expected = [
            node.children[0].children[1],
            node.children[0].children[2],
            node.children[0].children[3],
            node.children[1].children[0],
        ]
        self.assertCountEqual(result, expected)

    def test_complex_chain(self):
        node = self.node_test1
        result = solution(node, "div div > p")
        expected = [
            node.children[0].children[1],
            node.children[0].children[2],
            node.children[0].children[3],
            node.children[1].children[0],
        ]
        self.assertCountEqual(result, expected)

    def test_no_match_complex(self):
        node = self.node_test1
        result = solution(node, "div > div > div > a")
        expected = []
        self.assertCountEqual(result, expected)

    def test_multiple_spaces(self):
        node = self.node_test1
        result = solution(node, "div      p")
        expected = [
            node.children[0].children[1],
            node.children[0].children[2],
            node.children[0].children[3],
            node.children[1].children[0],
        ]
        self.assertCountEqual(result, expected)

    def test_repeated_matches(self):
        node = self.node_test1
        result = solution(node, "div p, div p")
        expected = [
            node.children[0].children[1],
            node.children[0].children[2],
            node.children[0].children[3],
            node.children[1].children[0],
        ]
        self.assertCountEqual(result, expected)

    def test_deeply_nested(self):
        deep_p = Node(tag="p", attributes={"class": "deep"}, text="Deep!")
        node = self.node_test1
        node.children[0].children[0].children = [deep_p]
        result = solution(node, "div p")
        expected = [
            node.children[0].children[1],
            node.children[0].children[2],
            node.children[0].children[3],
            node.children[1].children[0],
            deep_p,
        ]
        self.assertCountEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
