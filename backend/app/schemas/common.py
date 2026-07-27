from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Liste uçlarının ortak dönüş zarfı.

    Kural: JSON dizisi dönen HER top-level uç bunu döner. Detay yanıtlarının
    içindeki koleksiyonlar (CourseProfessorDetail.reviews gibi) sayfalanabilir
    liste değildir, düz dizi kalır.
    """

    items: List[T]
    total: int
    limit: int
    offset: int
