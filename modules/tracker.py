import numpy as np

class Tracker:
    def __init__(self, max_lost=30):
        self.next_id = 0
        self.objects = {} 
        self.max_lost = max_lost

    def update(self, rects, frame):
        updated_objects = {}
        crops_to_ocr = [] 

        for rect in rects:
            (tx1, ty1, tx2, ty2, tconf) = rect
            cx, cy = (tx1 + tx2) // 2, (ty1 + ty2) // 2

            matched_id = None
            min_dist = 99999
            for obj_id, (orect, lost, best_conf, is_identified) in self.objects.items():
                ox1, oy1, ox2, oy2 = orect
                ocx, ocy = (ox1 + ox2) // 2, (oy1 + oy2) // 2
                dist = np.sqrt((cx - ocx)**2 + (cy - ocy)**2)

                if dist < 100 and dist < min_dist:
                    min_dist = dist
                    matched_id = obj_id
            current_crop = frame[int(ty1):int(ty2), int(tx1):int(tx2)]
            
            if matched_id is not None:
                _, _, old_best_conf, is_identified = self.objects[matched_id]
                if not is_identified and tconf > 0.75:
                    crops_to_ocr.append((matched_id, current_crop))
                new_best_conf = max(tconf, old_best_conf)
                updated_objects[matched_id] = ((tx1, ty1, tx2, ty2), 0, new_best_conf, is_identified)
                del self.objects[matched_id]
            else:
                updated_objects[self.next_id] = ((tx1, ty1, tx2, ty2), 0, tconf, False)
                self.next_id += 1
        for obj_id, (rect, lost, best_conf, is_identified) in self.objects.items():
            if lost < self.max_lost:
                updated_objects[obj_id] = (rect, lost + 1, best_conf, is_identified)

        self.objects = updated_objects
        return updated_objects, crops_to_ocr

    def set_identified(self, obj_id):
        if obj_id in self.objects:
            rect, lost, conf, _ = self.objects[obj_id]
            self.objects[obj_id] = (rect, lost, conf, True)