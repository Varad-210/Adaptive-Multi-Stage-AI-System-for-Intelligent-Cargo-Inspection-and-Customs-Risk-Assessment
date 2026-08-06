import time

class MetricsTracker:
    def __init__(self):
        self.start_time = None
        self.pre_process_end = None
        self.inference_end = None
        self.post_process_end = None

    def start(self):
        self.start_time = time.time()
        
    def mark_pre_process(self):
        self.pre_process_end = time.time()
        
    def mark_inference(self):
        self.inference_end = time.time()
        
    def mark_post_process(self):
        self.post_process_end = time.time()
        
    def get_metrics(self):
        pre = (self.pre_process_end - self.start_time) * 1000 if self.pre_process_end else 0
        inf = (self.inference_end - self.pre_process_end) * 1000 if self.inference_end else 0
        post = (self.post_process_end - self.inference_end) * 1000 if self.post_process_end else 0
        total = pre + inf + post
        fps = 1000 / total if total > 0 else 0
        
        return {
            'preprocessing_time_ms': round(pre, 2),
            'inference_time_ms': round(inf, 2),
            'postprocessing_time_ms': round(post, 2),
            'processing_time_ms': round(total, 2),
            'fps': round(fps, 1)
        }
