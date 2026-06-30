from abc import ABC, abstractmethod

class OCRProvider(ABC):

    @abstractmethod
    def extract(self, file_path):
        pass