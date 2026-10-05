"""Portable documentation must link to resources that are actually packaged."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_package import validate_markdown_resources


class MarkdownResourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="easyviz-markdown-resource-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "easyviz"
        self.case = self.root / "skills/easyviz/assets/cases/distributions"
        self.case.mkdir(parents=True)
        self.readme = self.case / "README.md"

    def test_missing_sibling_case_or_excluded_render_is_rejected(self):
        for link in ("../../no-author-code/urschel-paired/README.md", "first-render/panel.png"):
            with self.subTest(link=link):
                self.readme.write_text(f"Historical evidence: [source]({link}).\n")
                before = self.readme.read_bytes()
                with self.assertRaisesRegex(ValueError, "Broken Markdown resource:.*README.md"):
                    validate_markdown_resources(self.root)
                self.assertEqual(self.readme.read_bytes(), before)

    def test_packaged_sibling_images_and_fragment_query_targets_pass(self):
        sibling = self.case.parent / "urschel-paired"
        sibling.mkdir()
        (sibling / "README.md").write_text("Paired observations\n")
        (self.case / "panel.png").write_bytes(b"packaged preview")
        (self.case / "source data.csv").write_text("id,value\n001,2\n")
        self.readme.write_text("[paired](../urschel-paired/README.md#observations)\n"
                               "![preview](panel.png?download=1#panel)\n"
                               "[data](source%20data.csv)\n"
                               "[data again](<source data.csv> \"source\")\n")
        self.assertEqual(validate_markdown_resources(self.root), 4)

    def test_external_urls_anchors_and_literal_templates_do_not_require_local_files(self):
        self.readme.write_text("[public evidence](https://github.com/example/repo/blob/main/first-render/panel.png)\n"
                               "[web](//example.test/resource) [mail](mailto:example@example.test)\n"
                               "[section](#details)\n"
                               "`[literal](missing-inline.md)`\n"
                               "```markdown\n[template](missing-template.svg)\n```\n"
                               "~~~markdown\n![template](missing-template.png)\n~~~\n"
                               "<!-- [hidden](missing-comment.md) -->\n"
                               "\\[escaped](missing-literal.md)\n"
                               "Template file path: `panel.png`.\n")
        self.assertEqual(validate_markdown_resources(self.root), 0)

    def test_existing_external_file_cannot_satisfy_a_portable_resource_link(self):
        outside = self.root.parent / "private.md"
        outside.write_text("outside the package\n")
        relative = "../../../../../../private.md"
        self.assertEqual((self.case / relative).resolve(), outside)
        for link in (relative, relative.replace("..", "%2E%2E")):
            with self.subTest(link=link):
                self.readme.write_text(f"[external local file]({link})\n")
                with self.assertRaisesRegex(ValueError, "Broken Markdown resource"):
                    validate_markdown_resources(self.root)
                self.assertEqual(outside.read_text(), "outside the package\n")


if __name__ == "__main__":
    unittest.main()
