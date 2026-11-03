from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import date, datetime


class GenreBase(BaseModel):
    genre_name: str = Field(..., min_length=1, max_length=50)


class GenreCreate(GenreBase):
    pass


class GenreResponse(GenreBase):
    genre_id: int

    class Config:
        from_attributes = True


class MovieBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    duration_min: int = Field(..., gt=0)
    language: str = Field(..., min_length=1)
    certificate: str = Field(..., pattern="^(U|UA|A)$")
    release_date: date
    rating: Optional[float] = Field(default=None, ge=0, le=10)
    poster_url: Optional[HttpUrl] = None


class MovieCreate(MovieBase):
    genre_ids: Optional[List[int]] = []


class MovieUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    duration_min: Optional[int] = Field(default=None, gt=0)
    language: Optional[str] = None
    certificate: Optional[str] = Field(default=None, pattern="^(U|UA|A)$")
    release_date: Optional[date] = None
    rating: Optional[float] = Field(default=None, ge=0, le=10)
    poster_url: Optional[HttpUrl] = None
    genre_ids: Optional[List[int]] = None


class MovieResponse(MovieBase):
    movie_id: int
    genres: List[GenreResponse] = []

    class Config:
        from_attributes = True


class MovieListResponse(BaseModel):
    movies: List[MovieResponse]
    total: int
    limit: int
    offset: int
