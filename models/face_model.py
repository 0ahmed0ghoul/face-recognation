from insightface.app import FaceAnalysis
from config import USE_GPU

def get_face_model():
    providers = ['CUDAExecutionProvider'] if USE_GPU else ['CPUExecutionProvider']
    model = FaceAnalysis(name='buffalo_s', providers=providers)
    model.prepare(ctx_id=0, det_size=(640, 640))
    return model
