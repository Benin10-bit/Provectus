import unittest,tempfile,hashlib
from pathlib import Path
from io import BytesIO
from PIL import Image
import pymupdf as fitz
from question_ingestor.pdf.recovery import unicode_candidate,isolate_raster
from question_ingestor.config import Config
from question_ingestor.parsing.rich import order_elements

class Recovery(unittest.TestCase):
 def test_candidate_never_claims_verified(self):
  c=unicode_candidate([0xD800,0xDECD]);self.assertEqual(c['text'],'𝛍');self.assertFalse(c['verified'])
 def test_candidate_preserves_distinct_low_surrogates(self):
  self.assertEqual(unicode_candidate([0xD800,0xDC61,0xD800,0xDC60])['text'],'𝑡𝑠')
 def test_unknown_pattern_has_no_proposal(self):
  self.assertIsNone(unicode_candidate([0xFFFD]));self.assertIsNone(unicode_candidate([0xD835,0xDECD]))
 def test_panels_order_left_then_right(self):
  es=[{'kind':'visual','page':1,'bbox':[262,412,478,655],'objects':['right']},{'kind':'visual','page':1,'bbox':[22,444,262,655],'objects':['left']}]
  self.assertEqual([e['objects'][0] for e in order_elements(es,Config())],['left','right'])
 def test_isolated_image_excludes_overlay_and_keeps_original(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);doc=fitz.open();p=doc.new_page();buf=BytesIO();Image.new('RGB',(100,80),'red').save(buf,format='PNG');xr=p.insert_image(fitz.Rect(20,20,120,100),stream=buf.getvalue());p.insert_text((30,50),'OVERLAY')
   info=p.get_image_info(hashes=True,xrefs=True)[0];obj={'id':'image1','xref':xr,'bbox':list(info['bbox']),'pixel_digest':info['digest'].hex()};page={'page':1,'objects':[obj],'drawings':[]};v={'objects':['image1'],'target':None};q={'content':[]}
   asset=isolate_raster(doc,page,v,q,root,Config());self.assertIsNotNone(asset);im=Image.open(root/asset['path']).convert('RGB');self.assertEqual(im.getpixel((20,30)),(255,0,0));self.assertIn('OVERLAY',p.get_text())
   q['content']=[{'kind':'text','page':1,'bbox':[30,30,80,60]}];self.assertIsNone(isolate_raster(doc,page,v,q,root,Config()))
