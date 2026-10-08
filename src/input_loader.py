from pathlib import Path
import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def read_uploaded_table(uploaded_file):
    """
    Streamlit UploadedFile을 DataFrame으로 읽는다.

    지원 형식:
    - CSV
    - XLSX

    실제 파일은 메모리에서 읽으며
    이 함수 자체는 디스크에 원본을 저장하지 않는다.
    """

    if uploaded_file is None:
        raise ValueError("업로드된 파일이 없습니다.")

    filename = uploaded_file.name
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"지원하지 않는 파일 형식입니다: {suffix} "
            f"(지원: CSV, XLSX)"
        )

    uploaded_file.seek(0)

    if suffix == ".csv":
        try:
            return pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            uploaded_file.seek(0)

            try:
                return pd.read_csv(
                    uploaded_file,
                    encoding="cp949",
                )
            except UnicodeDecodeError:
                uploaded_file.seek(0)

                return pd.read_csv(
                    uploaded_file,
                    encoding="euc-kr",
                )

    if suffix == ".xlsx":
        return pd.read_excel(
            uploaded_file,
            engine="openpyxl",
        )

    raise ValueError(
        f"읽을 수 없는 파일 형식입니다: {suffix}"
    )


def read_multiple_delivery_files(uploaded_files):
    """
    여러 월의 배달결과 업로드 파일을 읽어
    파일명과 DataFrame 목록으로 반환한다.
    """

    if not uploaded_files:
        raise ValueError(
            "배달결과 파일을 1개 이상 업로드해야 합니다."
        )

    results = []

    for uploaded_file in uploaded_files:
        df = read_uploaded_table(uploaded_file)

        results.append(
            {
                "filename": uploaded_file.name,
                "dataframe": df,
            }
        )

    return results
