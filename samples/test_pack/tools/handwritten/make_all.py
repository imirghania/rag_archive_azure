"""Regenerates everything: paper, texts, previews. Run: uv run python samples/test_pack/tools/handwritten/make_all.py"""
import make_paper
import make_preview
import make_texts

make_paper.main()
make_texts.main()
make_preview.main()
