import sys,tempfile,unittest
from pathlib import Path
import pymupdf as fitz
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from figure_gallery import scan

class RasterScan(unittest.TestCase):
    def test_image_placement_without_text_image_blocks_and_distant_mention(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);pdf=root/'paper.pdf';d=fitz.open();p=d.new_page()
            pix=fitz.Pixmap(fitz.csRGB,fitz.IRect(0,0,300,120),False);pix.clear_with(120)
            p.insert_image(fitz.Rect(50,50,350,170),stream=pix.tobytes('png'))
            p.insert_text((50,190),'Figure 1');p.insert_text((50,205),'Market concentration and rates')
            p.insert_text((50,450),'Figure 2 shows other results in the discussion.')
            d.save(pdf);d.close();result=scan(pdf,root/'scan')
            self.assertEqual(result['candidates'],1)
            self.assertTrue((root/'scan/F1-original.png').exists())

if __name__=='__main__':unittest.main()
