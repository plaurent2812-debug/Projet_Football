import { useParams, useNavigate } from "react-router-dom"
import { useState, useEffect } from "react"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function NHLMatchDetail() {
    const { id } = useParams()
    const navigate = useNavigate()

    return (
        <div className="space-y-6 p-6">
            <Button variant="ghost" onClick={() => navigate(-1)} className="gap-2 pl-0 hover:pl-2 transition-all">
                <ArrowLeft className="w-4 h-4" />
                Retour
            </Button>

            <div className="text-center py-12">
                <h1 className="text-2xl font-bold">Détails du match {id}</h1>
                <p className="text-muted-foreground">Analyses détaillées à venir.</p>
            </div>
        </div>
    )
}
