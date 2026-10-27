from pydantic import BaseModel, ConfigDict


class PopularityStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    wishlist_count: int = 0
    sales_count: int = 0


class MostWishedGame(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    wishlist_count: int


class MostPurchasedGame(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    sales_count: int
