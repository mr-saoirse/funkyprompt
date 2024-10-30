import PyPDF2
import fitz
from PIL import Image, ImageOps
import io
from pdf2image import convert_from_path
import typing
from tenacity import retry, wait_fixed, stop_after_attempt
import traceback
import json
from funkyprompt.services import fs


class PdfParser:
    def __init__(
        self,
        uri,
        min_size=(300, 300)
    ):
        self._uri = uri
        pdf_path = (
            io.BytesIO(open(uri, "rb").read())
            if not "s3://" in uri
            else fs.open(uri, "rb")
        )

        pdf_reader = PyPDF2.PdfReader(stream=pdf_path)
        self._parsed_text = []
        # we call out to LLM to describe all images
        self._sketch_texts = []
        self._num_pages = len(pdf_reader.pages)

        # here we add the text parsed from each page
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if len(text.strip()) > 0:
                self._parsed_text.append(text)
            
        return

        self._page_images = []
        self._page_image_info = []
        with fitz.open(stream=pdf_path) as pdf_document:
            # https://github.com/pymupdf/PyMuPDF/issues/385
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                iminfo = page.get_image_info()

                self._page_image_info.append(iminfo)
                # here we add separate images on each page
                image_list = []
                for ii, img in enumerate(page.get_images(full=True)):
                    # -0 im transform used below
                    transform = iminfo[ii].get("transform")

                    xref = img[0]
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(image_bytes))

                    if image.size[0] < min_size[0] or image.size[1] < min_size[1]:
                        continue
                    # third comp for rotation
                    # if transform and "-" in str(transform[2]):
                    #     image = ImageOps.flip(image)
                    image_list.append(image)

                self._page_images.append(image_list)

        # these are the full page scans of the page
        self._image_scans = []
        try:
            if "s3://" in uri:
                raise NotImplementedError("more fs stuff todo")
                self._image_scans = fs.apply(uri, fn=convert_from_path)
            else:
                self._image_scans = convert_from_path(uri)
        except:
            raise

        assert len(self._image_scans) == len(
            self._page_images
        ), "we expect the same number of pages as page data"
        assert len(self._parsed_text) == len(
            self._page_images
        ), "we expect the same number of pages as page data"

        self._page_parsers = []

        # for i in range(self._num_pages):
        #     self._page_parsers.append(
        #         cls(
        #             filename=uri,
        #             index=i,
        #             page_text=self._parsed_text[i],
        #             page_scan=self._image_scans[i],
        #             page_images=self._page_images[i],
        #         )
        #     )


    def get_page_image_text(cls, prompt=None, include_page_scans=True):
        """
        parse images from pdf. If we are taking the time to describe specific images doing the page scans seems worth it
        however, there could be text files with LOTS of pages and maybe we only want to describe pages that
        have image content e.g. at east one image
        """
        
        raise NotImplementedError("TODO")

        if not prompt:
            prompt = """Please describe the image content in detail. Resonance is a garment manufacturing business. If the image is a technical design of a garment describe it in detail.
            If the image is a diagram, extract the content into explanations. If the image is a table or graph, describe the numerical data in detail.
            All output should be in english
            """

        root = "/".join(cls._uri.split("/")[:-1])
        filename = cls._uri.split("/")[-1]
        root = f"{root}/{fun.utils.res_hash(filename)}"
        if cls._sketch_texts:
            return cls._sketch_texts
        cls._sketch_texts = []

        skip_scans_without_images = False
        N = len(cls._page_images)
        if N > 20:
            skip_scans_without_images = True

        def filter_for_size(images, min_side=300):
            """
            ignore if both dimension is small
            """
            return [i for i in images if i.size[0] > min_side and i.size[1] > min_side]

        for page, page_images in enumerate(cls._page_images):

            page_images = filter_for_size(page_images)
            if include_page_scans:
                """
                we add the overall page description at the end if we can
                we have asserted at top that we have as many image scans as pages
                we are being efficient for large (>20) pages if we should do anything at all
                by filtering for images (not logos) bigger than a certain size we can be
                sure we only bother scraping beyond if there is interesting visual content
                """
                if not skip_scans_without_images:
                    page_images.append(cls._image_scans[page])

            for j, sketch_image in enumerate(page_images):
                try:
                    # print(sketch_image.size) #if the image is very small we probably want to skip it
                    s = describe_visual_image(
                        sketch_image,
                        question_relating_to_url_passed=prompt,
                        cache_location=f"{root}/page{page}/{j}",
                        suffix=".pdf",
                    )
                    cls._sketch_texts.append(
                        f"""
                            **{filename} - Page {page} image {j} **
                            ```
                            {s}
                            ```
                            """
                    )
                except Exception as ex:
                    raise

        return cls._sketch_texts


    def __getitem__(self, key):
        return self._page_parsers[key]

    def parse(self, out_key, prompt=None, from_cache=False, num_workers=4):
        """
        we read the document in parallel - if the prompt is passed we could guide to some specific information but generally we have a standard prompt for garment development
        """

        path = f"{out_key}/reader_cached.json"

        if from_cache and fs.exists(path):
            return fs.read(path)

        import concurrent.futures
        from functools import partial

        def f(i, uri, key):
            tp = PdfParser(uri)
            try:
                return tp[i].parse(out_key=f"{key}/{i}")
            except Exception as ex:
                # raise  # While testing at least
                return {"error": f"failed to parse page {i} - {ex}"}

        f = partial(f, uri=self._uri, key=out_key)

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_results = [executor.submit(f, i) for i in range(self._num_pages)]
            results = [
                future.result()
                for future in concurrent.futures.as_completed(future_results)
            ]

        return results


