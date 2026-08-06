import { describe, expect, it, vi } from "vitest";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { MemoryRouter, Route, Routes } from "react-router-dom";

import { useContext } from "react";

import api from "../api/axios";

import AuthProvider from "../context/AuthContext";

import { AuthContext } from "../context/auth-context";

import ProtectedRoute from "../components/ProtectedRoute";

import VerifyOtp from "../pages/Auth/VerifyOtp";


vi.mock("../api/axios", () => ({
    default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));


const KULLANICI = {
    role: "student",
    current_grade: 3,
    enrollment_year: 2023,
    is_verified: true,
    department_id: 3,
    department_name: "Bilgisayar Mühendisliği",
};


function Sonda() {

    const { user } = useContext(AuthContext);

    return <p>rol: {user?.role ?? "yok"}</p>;

}


const ekranaBas = (anaSayfa) =>
    render(
        <MemoryRouter initialEntries={["/kayit/dogrula"]}>
            <AuthProvider>
                <Routes>
                    <Route path="/kayit/dogrula" element={<VerifyOtp />} />
                    <Route path="/" element={anaSayfa} />
                    <Route path="/giris" element={<p>Giriş ekranı</p>} />
                </Routes>
            </AuthProvider>
        </MemoryRouter>
    );


const kodGir = () => {

    fireEvent.change(screen.getByPlaceholderText("E-posta"), {
        target: { value: "ogrenci@pau.edu.tr" },
    });

    fireEvent.change(screen.getByPlaceholderText("Doğrulama kodu"), {
        target: { value: "123456" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Doğrula" }));

};


describe("OTP doğrulama", () => {

    it("token'ı saklar ve kullanıcıyı doldurur", async () => {

        api.post.mockResolvedValue({ data: { access_token: "jeton", token_type: "bearer" } });

        api.get.mockResolvedValue({ data: KULLANICI });

        ekranaBas(<Sonda />);

        kodGir();

        await waitFor(() => expect(localStorage.getItem("token")).toBe("jeton"));

        expect(api.post).toHaveBeenCalledWith("/auth/verify-otp", {
            email: "ogrenci@pau.edu.tr",
            otp: "123456",
        });

        expect(await screen.findByText("rol: student")).toBeInTheDocument();

    });

    it("giriş sonrası ProtectedRoute kullanıcıyı geri atmaz", async () => {

        api.post.mockResolvedValue({ data: { access_token: "jeton", token_type: "bearer" } });

        api.get.mockResolvedValue({ data: KULLANICI });

        ekranaBas(

            <ProtectedRoute>
                <p>Gizli sayfa</p>
            </ProtectedRoute>

        );

        kodGir();

        expect(await screen.findByText("Gizli sayfa")).toBeInTheDocument();

        expect(screen.queryByText("Giriş ekranı")).not.toBeInTheDocument();

    });

});
