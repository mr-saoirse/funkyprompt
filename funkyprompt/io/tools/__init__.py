import itertools


def iter_doc_pages(file, **kwargs):
    """
    simple document reader - want to expand this to model text in more interesting ways

    BC = AbstractVectorStoreEntry.create_model("BookChapters")
    store = VectorDataStore(BC)
    for i, page in enumerate(iter_doc_pages(file)):
        record = BC(name = "LongitudePage{i}", text=page)
        store.add(record)

    """

    import fitz

    def process_page(page, headers={}):
        def line_detail(spans):
            return [(s["text"], round(s["size"]), s["font"]) for s in spans]

        spans = [
            line_detail(line["spans"])
            for block in page
            for line in block.get("lines", [])
        ]
        spans = list(itertools.chain.from_iterable(spans))
        # TODO implement the flatten ligic based on header changes with carry on context in headers from previous pages
        lines = "\n".join([line[0] for line in spans])
        return lines

    with fitz.open(file) as pdf_document:
        for i in range(pdf_document.page_count):
            page = pdf_document.load_page(i).get_text("dict")
            yield process_page(page["blocks"])
