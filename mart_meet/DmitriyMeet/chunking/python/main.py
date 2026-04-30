import pymupdf
from utils import *
from dotenv import load_dotenv
from clearml import Task

load_dotenv()
task = Task.init(project_name='Chunking', task_name='process_dataset_VladPC')
logger = task.get_logger()


from elasticsearch import Elasticsearch
ES = Elasticsearch("http://192.168.0.59:9221", basic_auth=["user", "infini_rag_flow"], verify_certs=False)

# Здесь создаются индексы в которых хранятся чанки. Лучше создать с новыми именами и указать нужную размерность
create_index_chunks(ES, "chunking_index", 1024)
create_index_books(ES, "book_index", 1024)

# Отцифрованные учебники, которые мне предоставили, имеют удобную структуру чтобы их читать
# collect_pdf_path проходится по этой структуре и собирает пути до pdf
pdf_paths = collect_pdf_paths(r"D:\chunking\Chemical Technology\article")
for index, pdf in enumerate(pdf_paths):
    logger.report_scalar(
        title="Progress",
        series="Processed Files",
        value=index + 1,
        iteration=index
    )

    doc = pymupdf.open(pdf)  # open a document
    pages = []
    for page in doc:  # iterate the document pages
        page = clean_article_text(page.get_text())  # get plain text encoded as UTF-8
        pages.append(page)
    insert_file_record(ES, "book_index", pages[0], pdf.name) # Первый чанк попадает в индекс в котором инфа с книгами связана
    insert_chunk_records_bulk(ES, "chunking_index", pages, pdf.name) # все чанки загружаются в общее чанк хранилище
