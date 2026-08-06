import { describe, expect, it, vi } from "vitest";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { MemoryRouter } from "react-router-dom";

import api from "../api/axios";

import CreateReview from "../pages/Reviews/CreateReview";


vi.mock("../api/axios", () => ({
    default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));


describe("CreateReview", () => {

    it("eşleşme id'si ve üç skorla gönderir", async () => {

        api.post.mockResolvedValue({ data: { id: 1, status: "pending" } });

        render(
            <MemoryRouter initialEntries={["/yorum-yap?course_professor_id=7"]}>
                <CreateReview />
            </MemoryRouter>
        );

        fireEvent.change(screen.getByLabelText("Anlatım"), { target: { value: "5" } });

        fireEvent.change(screen.getByLabelText("Zorluk"), { target: { value: "2" } });

        fireEvent.change(screen.getByLabelText("Adalet"), { target: { value: "4" } });

        fireEvent.change(screen.getByLabelText(/Yorum/), { target: { value: "Anlatımı iyiydi" } });

        fireEvent.click(screen.getByRole("button", { name: "Gönder" }));

        await waitFor(() =>

            expect(api.post).toHaveBeenCalledWith("/reviews", {
                course_professor_id: 7,
                teaching_score: 5,
                difficulty_score: 2,
                fairness_score: 4,
                comment: "Anlatımı iyiydi",
            })

        );

        // 201 dönse de yorum yayında değil; ekran bunu söylemeli.
        expect(await screen.findByText("Yorumunuz incelemede")).toBeInTheDocument();

    });

});
