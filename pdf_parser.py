
import os
import re
import io
import tempfile

from pdfminer.layout import LTPage, LTText, LAParams, LTTextBox, LTRect, LTLine, LTFigure, LTImage, LTTextLine, LTChar
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator

from PyPDF2 import PdfFileReader, PdfFileWriter


class PageNotFoundError(Exception):
    """Exception class for accessing not existing page from a pdf_parser object."""
    pass

class row():
    """Row bound by lower and upper y-coordinates."""
    def __init__(self, y0 = -1, y1 = -1):
        self.y0 = y0
        self.y1 = y1

class column():
    """Column bound by left and right x-coordinates."""
    def __init__(self, x0 = -1, x1 = -1):
        self.x0 = x0
        self.x1 = x1
        
class box():
    """Box bound by a given row and column."""
    def __init__(self, myrow = row(), mycolumn = column()):
        self.myrow = myrow
        self.mycolumn = mycolumn
        
class text_box():
    """TextBox bound by a box and containing some text."""
    def __init__(self, lobj):
        self.text = lobj.get_text()
        self.myrow = row(lobj.x0, lobj.x1)
        self.mycolumn = column(lobj.y0, lobj.y1)
        self.mybox = box(self.row, self.column)
        self.mybbox = lobj.bbox
        
def get_lt_texts(lts):
    if isinstance(lts, LTText):
        return []
    
    lt_texts = []
    try:
        list(lts)
    except:
        return []
    for ltobj in lts:
        try:
            list(ltobj)
        except:
            continue
        if check_text_group(ltobj):
            lt_texts.append(get_LTTextBox(ltobj))
        else:
            lt_texts.extend(get_lt_texts(ltobj))
    return lt_texts  

def check_text_group(ltobj):
    return all([isinstance(i, LTChar) for i in list(ltobj)])

def get_LTTextBox(ltobj):
    lt_text_obj = LTTextBox()
    lt_text_obj.set_bbox(ltobj.bbox)
    
    if check_text_group(ltobj):
        for lt_char in list(ltobj):
            lt_text_obj.add(lt_char)
        
    return lt_text_obj    
        
        
class page_parser():
    """
    Page_parser class for parsing functionality of a particular page of a pdf file, with help of LTPage object from pdfminer.layout module.
    """
    
    def __init__(self, layout):
        """
        Takes LTPage object and initializes list of children LT objects from that page.
        """
        
        self.layout = layout
        self.lobjs_all = list(layout)
        self.lobjs_text = []
        self.lobjs_text_line = []
        self.lobjs_rect = []
        self.lobjs_line = []
        self.lobjs_fig = []
        self.lobjs_img = []
        
        for lobj in self.lobjs_all:
            if isinstance(lobj, LTText):
                self.lobjs_text.append(lobj)
            
            if isinstance(lobj, LTRect):
                self.lobjs_rect.append(lobj)
            
            elif isinstance(lobj, LTLine):
                self.lobjs_line.append(lobj)

            elif isinstance(lobj, LTFigure):
                self.lobjs_fig.append(lobj)
                
        for lobj_fig in self.lobjs_fig:
            for lobj in list(lobj_fig):
                if isinstance(lobj, LTImage):
                    self.lobjs_img.append(lobj)
                    
        for lobj_text in self.lobjs_text:
            for lobj in list(lobj_text):
                if isinstance(lobj, LTTextLine):
                    self.lobjs_text_line.append(lobj)
                        
        self.lobjs_text.extend(get_lt_texts(self.lobjs_fig))
        self.lobjs_text_line.extend(get_lt_texts(self.lobjs_fig))
                    
                    
    def get_layout(self):
        return self.layout
                
    def find(self, text = '', constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find a text_box containing  particular string within constraints.
        
        Args:
            text (str): text to searched
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            found LTTextBox object
        """
        
        bbox = LTTextBox()
        if constraint == None:
            for lobj in self.lobjs_text:
                if text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split())):
                    return lobj
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_text:
                if bbox.is_voverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                     return lobj
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_text:
                if bbox.is_hoverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                    return lobj
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_text:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                    return lobj
                
    def find_all(self, text = '', constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find all text_box containing  particular string within constraints.
        
        Args:
            text (str): text to searched
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            list of found LTTextBox objects
        """
        
        bbox = LTTextBox()
        
        lobjs = []
        
        if constraint == None:
            for lobj in self.lobjs_text:
                if text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split())):
                    lobjs.append(lobj)
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_text:
                if bbox.is_voverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                     lobjs.append(lobj)
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_text:
                if bbox.is_hoverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                    lobjs.append(lobj)
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_text:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                    lobjs.append(lobj)
                    
        return lobjs
    
    def find_text_line(self, text = '', constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find a text_line containing  particular string within constraints.
        
        Args:
            text (str): text to searched
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            found LTTextLine object
        """
        
        bbox = LTTextBox()
        
        if constraint == None:
            for lobj in self.lobjs_text_line:
                
                if text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split())):
                    
                    return lobj
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_text_line:
                if bbox.is_voverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                     return lobj
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_text_line:
                if bbox.is_hoverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                    return lobj
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_text_line:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                    return lobj
                
    def find_text_line_all(self, text = '', constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find all text_line containing  particular string within constraints.
        
        Args:
            text (str): text to searched
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            list of found LTTextLine objects
        """
        
        bbox = LTTextBox()
        
        lobjs = []
        
        if constraint == None:
            for lobj in self.lobjs_text_line:
                
                if text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split())):
                    lobjs.append(lobj)
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_text_line:
                if bbox.is_voverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                     lobjs.append(lobj)
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_text_line:
                if bbox.is_hoverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                    lobjs.append(lobj)
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_text_line:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj) and (text.lower() in " ".join(lobj.get_text().lower().split()) or re.search(text.lower(), " ".join(lobj.get_text().lower().split()))):
                    lobjs.append(lobj)
                    
        return lobjs
    
    def find_rect(self, constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find a rectangle within constraints.
        
        Args:
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            found LTRect object
        """
        
        bbox = LTRect(1, (mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
        
        if constraint == None:
            for lobj in self.lobjs_rect:
                return lobj
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_rect:
                if bbox.is_voverlap(lobj):
                     return lobj
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_rect:
                if bbox.is_hoverlap(lobj):
                    return lobj
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_rect:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj):
                    return lobj
                
                
    def find_rect_all(self, constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find all rectangles within constraints.
        
        Args:
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            list of found LTRect objects
        """
        
        bbox = LTRect(1, (mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
        
        lobjs = []
        
        if constraint == None:
            for lobj in self.lobjs_rect:
                lobjs.append(lobj)
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_rect:
                if bbox.is_voverlap(lobj):
                     lobjs.append(lobj)
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_rect:
                if bbox.is_hoverlap(lobj):
                    lobjs.append(lobj)
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_rect:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj):
                    lobjs.append(lobj)
                    
        return lobjs
    
    def find_fig(self, constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find a figure within constraints.
        
        Args:
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            found LTFigure object
        """
        
        bbox = LTRect(1, (mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
        
        if constraint == None:
            for lobj in self.lobjs_fig:
                return lobj
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_fig:
                if bbox.is_voverlap(lobj):
                     return lobj
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_fig:
                if bbox.is_hoverlap(lobj):
                    return lobj
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_fig:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj):
                    return lobj
                
    def find_fig_all(self, constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find all figures within constraints.
        
        Args:
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            list of found LTFigure objects
        """
        
        bbox = LTRect(1, (mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
        
        lobjs = []
        
        if constraint == None:
            for lobj in self.lobjs_fig:
                lobjs.append(lobj)
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_fig:
                if bbox.is_voverlap(lobj):
                     lobjs.append(lobj)
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_fig:
                if bbox.is_hoverlap(lobj):
                    lobjs.append(lobj)
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_fig:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj):
                    lobjs.append(lobj)
                    
        return lobjs
    
    def find_img(self, constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find an image within constraints.
        
        Args:
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            found LTImage object
        """
        
        bbox = LTRect(1, (mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
        
        if constraint == None:
            for lobj in self.lobjs_img:
                return lobj
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_img:
                if bbox.is_voverlap(lobj):
                     return lobj
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_img:
                if bbox.is_hoverlap(lobj):
                    return lobj
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_img:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj):
                    return lobj
                
    def find_img_all(self, constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find all images within constraints.
        
        Args:
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            list of found LTImage objects
        """
        
        bbox = LTRect(1, (mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
        
        lobjs = []
        
        if constraint == None:
            for lobj in self.lobjs_img:
                lobjs.append(lobj)
        
        elif constraint == 'row':
            bbox.set_bbox((-1, myrow.y0, -1, myrow.y1))

            for lobj in self.lobjs_img:
                if bbox.is_voverlap(lobj):
                     lobjs.append(lobj)
        
        elif constraint == 'column':
            bbox.set_bbox((mycolumn.x0, -1, mycolumn.x1, -1))
             
            for lobj in self.lobjs_img:
                if bbox.is_hoverlap(lobj):
                    lobjs.append(lobj)
             
        elif constraint == 'box':
            if mybox != None:
                myrow = mybox.myrow
                mycolumn = mybox.mycolumn
             
            bbox.set_bbox((mycolumn.x0, myrow.y0, mycolumn.x1, myrow.y1))
             
            for lobj in self.lobjs_img:
                if bbox.is_hoverlap(lobj) and bbox.is_voverlap(lobj):
                    lobjs.append(lobj)
                    
        return lobjs
    
    
class pdf_parser():
    """Class for providing functionality to get information from different pages of a pdf file."""
    
    def __init__(self, fp):
        """Takes a file-pointer of a pdf file and initializes page_parser objects for each page and stores them."""
        
        fp.seek(0)
        self.pdf_reader = PdfFileReader(fp)
        
        fp.seek(0)
        
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        pages = PDFPage.get_pages(fp)
        
        self.layout_list = []
        self.page_list = []
        
        for page in list(pages):
            interpreter.process_page(page)
            layout = device.get_result()
            self.layout_list.append(layout)
            self.page_list.append(page_parser(layout))
            
    def get__lt_page(self, pageno):
        """
        Get page_parser object of a particular page by page-no from the pdf_parser object.
        
        Args:
            pageno (int): page number of the required page
            
        Returns:
            page_parser object of that page
        """
        
        page_len = len(self.layout_list)
        if pageno < page_len and pageno >= -page_len:
            return self.layout_list[pageno]
        else:
            raise PageNotFoundError('Required page number not found')
            
    def get_page_stream(self, pageno):
        page_len = len(self.layout_list)
        if pageno < page_len and pageno >= -page_len:
            writer = PdfFileWriter()
            writer.addPage(self.pdf_reader.getPage(pageno))
            stream = io.BytesIO()
            writer.write(stream)
            return stream.getvalue()
        else:
            raise PageNotFoundError('Required page number not found')
    
    def find_page_stream(self, text, constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        pageno = self.find_page_no(text, constraint = None, mybox = None, myrow = row(), mycolumn = column())
        
        if pageno != None:
            writer = PdfFileWriter()
            writer.addPage(self.pdf_reader.getPage(pageno))
            stream = io.BytesIO()
            writer.write(stream)
            return stream.getvalue()
        
        return b''
            
    def get_page(self, pageno):
        """
        Get page_parser object of a particular page by page-no from the pdf_parser object.
        
        Args:
            pageno (int): page number of the required page
            
        Returns:
            page_parser object of that page
        """
        
        page_len = len(self.page_list)
        if pageno < page_len and pageno >= -page_len:
            return self.page_list[pageno]
        else:
            raise PageNotFoundError('Required page number not found')
            
    def get_no_pages(self):
        """Get number of pages in the pdf file."""
        
        return len(self.page_list)
    
    def get_pages(self):
        """Get list of page_parser objects of all pages of the pdf file."""
        
        return self.page_list
    
    def find_page_no(self, text="", constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find a page_no from the pdf containing a particular text within constraints
        
        Args:
            text (str): text to searched
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            page_parser object of the found page, else None
        
        """
        
        for i,page in enumerate(self.page_list):
            if page.find(text = text, constraint = constraint, mybox = mybox, myrow = myrow, mycolumn = mycolumn):
                return i
            
        return None
    
    def find_page(self, text = "", constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find a page from the pdf containing a particular text within constraints
        
        Args:
            text (str): text to searched
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            page_parser object of the found page, else None
        
        """
        
        for page in self.page_list:
            if page.find(text = text, constraint = constraint, mybox = mybox, myrow = myrow, mycolumn = mycolumn):
                return page
            
        return None
    
    def find_page_all(self, text = "", constraint = None, mybox = None, myrow = row(), mycolumn = column()):
        """
        Find all pages from the pdf containing a particular text within constraints
        
        Args:
            text (str): text to searched
            constraint (str): constraint to be applied while searching for text-box, value from ['row', 'column', 'box']
            mybox (box): box object for searching within a particular box
            myrow (row): row object to constrain the search to a particular row
            mycolumn (column): column object to constrain the search to a particular column
            
        Returns:
            list of page_parser objects of the found pages, else empty-list
        
        """
        
        found_page_list = []
        for page in self.page_list:
            if page.find(text = text, constraint = constraint, mybox = mybox, myrow = myrow, mycolumn = mycolumn):
                found_page_list.append(page)
            
        return found_page_list