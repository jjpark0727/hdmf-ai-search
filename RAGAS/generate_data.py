import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.testset import TestsetGenerator
from ragas.testset.synthesizers import (
    SingleHopSpecificQuerySynthesizer,
    MultiHopAbstractQuerySynthesizer,
    MultiHopSpecificQuerySynthesizer,
)
from ragas.testset.transforms import (
    Parallel,
    EmbeddingExtractor,
    SummaryExtractor,
    CustomNodeFilter,
    CosineSimilarityBuilder,
)
from ragas.testset.transforms.extractors import NERExtractor, TopicDescriptionExtractor
from ragas.testset.transforms.relationship_builders import OverlapScoreBuilder
from ragas.testset.graph import NodeType
from ragas.utils import num_tokens_from_string

# ── 설정 ──────────────────────────────────────────────
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DOCS_DIR = Path(__file__).resolve().parent / "docs"
OUTPUT_CSV = Path(__file__).resolve().parent / "ragas_dataset.csv"
TEST_SIZE_PER_FOLDER = 15  # 폴더당 생성할 테스트 샘플 수

# ── 1. PDF 로드 (폴더별 그룹핑, 페이지 단위) ──────────
def load_pdfs_by_folder(docs_dir: Path) -> dict[str, list[Document]]:
    """폴더별로 PDF를 페이지 단위로 로드한다. {폴더명: [Document, ...]} 형태로 반환."""
    folder_docs = {}
    for folder in sorted(docs_dir.iterdir()):
        if not folder.is_dir():
            continue
        folder_name = folder.name
        documents = []
        for pdf_path in sorted(folder.glob("*.pdf")):
            pdf_filename = pdf_path.name
            doc = fitz.open(str(pdf_path))
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if not text.strip():
                    continue
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "folder_name": folder_name,
                            "pdf_filename": pdf_filename,
                            "page_number": page_num + 1,  # 1-based
                        },
                    )
                )
            doc.close()
        if documents:
            folder_docs[folder_name] = documents
    return folder_docs


# ── 2. 커스텀 transforms (HeadlineSplitter 제외) ───────
def build_custom_transforms(llm, embeddings):
    """HeadlineSplitter를 제외한 커스텀 transform 파이프라인을 구성한다."""
    filter_docs = lambda node: node.type == NodeType.DOCUMENT
    filter_min_tokens = lambda node: (
        node.type == NodeType.DOCUMENT
        and num_tokens_from_string(node.properties.get("page_content", "")) > 100
    )

    summary_extractor = SummaryExtractor(llm=llm, filter_nodes=filter_min_tokens)
    summary_emb_extractor = EmbeddingExtractor(
        embedding_model=embeddings,
        property_name="summary_embedding",
        embed_property_name="summary",
        filter_nodes=filter_min_tokens,
    )
    cosine_sim_builder = CosineSimilarityBuilder(
        property_name="summary_embedding",
        new_property_name="summary_similarity",
        threshold=0.5,
        filter_nodes=filter_min_tokens,
    )
    ner_extractor = NERExtractor(llm=llm)
    ner_overlap_sim = OverlapScoreBuilder(threshold=0.01)
    theme_extractor = TopicDescriptionExtractor(llm=llm, filter_nodes=filter_docs)
    node_filter = CustomNodeFilter(llm=llm)

    return [
        summary_extractor,
        node_filter,
        Parallel(summary_emb_extractor, theme_extractor, ner_extractor),
        Parallel(cosine_sim_builder, ner_overlap_sim),
    ]


# ── 3. context ↔ 원본 문서 매칭 ────────────────────────
def find_source_metadata(context: str, source_docs: list[Document]) -> dict:
    """생성된 context 텍스트가 어떤 원본 페이지에서 왔는지 찾는다."""
    best_match = None
    best_overlap = 0
    for doc in source_docs:
        # context와 원본 페이지 텍스트의 겹침 정도를 측정
        overlap = len(set(context.split()) & set(doc.page_content.split()))
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = doc
    if best_match:
        return best_match.metadata
    return {"folder_name": "", "pdf_filename": "", "page_number": ""}


# ── 4. 메인 실행 ──────────────────────────────────────
def main():
    # 폴더별 문서 로드
    print("📄 PDF 문서 로드 중...")
    folder_docs = load_pdfs_by_folder(DOCS_DIR)
    for folder_name, docs in folder_docs.items():
        print(f"   [{folder_name}] {len(docs)}개 페이지")

    # LLM / Embedding 모델 초기화
    llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini"))
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings())

    # Query 분포 설정 (한국어 프롬프트 적용)
    synthesizers = [
        SingleHopSpecificQuerySynthesizer(llm=llm),
        MultiHopAbstractQuerySynthesizer(llm=llm),
        MultiHopSpecificQuerySynthesizer(llm=llm),
    ]
    for s in synthesizers:
        for attr_name in dir(s):
            if "prompt" in attr_name and not attr_name.startswith("_"):
                prompt = getattr(s, attr_name)
                if hasattr(prompt, "language"):
                    prompt.language = "korean"

    query_distribution = [
        (synthesizers[0], 0.4),
        (synthesizers[1], 0.3),
        (synthesizers[2], 0.3),
    ]

    # 커스텀 transforms 구성
    custom_transforms = build_custom_transforms(llm, embeddings)

    # RAGAS 0.4.x 컬럼명 → 원하는 컬럼명 매핑
    rename_map = {
        "user_input": "question",
        "reference_contexts": "context",
        "reference": "ground_truth",
        "synthesizer_name": "evolution_type",
    }

    # ── 폴더별 독립 생성 ──────────────────────────────
    all_dfs = []
    for folder_name, docs in folder_docs.items():
        print(f"\n🔄 [{folder_name}] Knowledge Graph 구축 및 데이터셋 생성 중 "
              f"(test_size={TEST_SIZE_PER_FOLDER})...")

        # 폴더마다 새로운 generator (독립 knowledge graph)
        generator = TestsetGenerator(llm=llm, embedding_model=embeddings)

        testset = generator.generate_with_langchain_docs(
            documents=docs,
            testset_size=TEST_SIZE_PER_FOLDER,
            transforms=custom_transforms,
            query_distribution=query_distribution,
        )

        df = testset.to_pandas()
        df = df.rename(columns=rename_map)

        # 메타데이터 컬럼 추가
        folder_names = []
        pdf_filenames = []
        page_numbers = []

        for _, row in df.iterrows():
            contexts = row.get("context", [])
            ctx_text = contexts[0] if isinstance(contexts, list) and contexts else str(contexts)
            meta = find_source_metadata(ctx_text, docs)
            folder_names.append(meta["folder_name"])
            pdf_filenames.append(meta["pdf_filename"])
            page_numbers.append(meta["page_number"])

        df["folder_name"] = folder_names
        df["pdf_filename"] = pdf_filenames
        df["page_number"] = page_numbers

        all_dfs.append(df)
        print(f"   [{folder_name}] {len(df)}개 샘플 생성 완료")

    # ── 전체 합치기 및 저장 ───────────────────────────
    final_df = pd.concat(all_dfs, ignore_index=True)

    # 최종 컬럼 순서 정리
    final_columns = [
        "question",
        "context",
        "ground_truth",
        "evolution_type",
        "folder_name",
        "pdf_filename",
        "page_number",
    ]
    existing_cols = [c for c in final_columns if c in final_df.columns]
    extra_cols = [c for c in final_df.columns if c not in final_columns]
    final_df = final_df[existing_cols + extra_cols]

    # CSV 저장
    final_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n✅ 데이터셋 저장 완료: {OUTPUT_CSV}")
    print(f"   총 {len(final_df)}개 샘플 (폴더 {len(folder_docs)}개)")
    print(final_df.head())


if __name__ == "__main__":
    main()
